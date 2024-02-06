import csv
from decimal import Decimal
import dataclasses
from datetime import datetime, timedelta
import logging
import os

from coldfront_plugin_cloud import attributes
from coldfront_plugin_cloud import utils

import boto3
from django.core.management.base import BaseCommand
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class InvoiceRow:
    InvoiceMonth: str = ""
    Project_Name: str = ""
    Project_ID: str = ""
    PI: str = ""
    Invoice_Email: str = ""
    Invoice_Address : str = ""
    Institution: str = ""
    Institution_Specific_Code: str = ""
    Invoice_Type_Hours: int = 0
    Invoice_Type: str = ""
    Rate: Decimal = 0
    Cost: Decimal = 0


    @classmethod
    def get_headers(cls):
        """Returns all headers for display."""
        return [
            "Invoice Month",
            "Project - Allocation",
            "Project - Allocation ID",
            "Manager (PI)",
            "Invoice Email",
            "Invoice Address",
            "Institution",
            "Institution - Specific Code",
            "SU Hours (GBhr or SUhr)",
            "SU Type",
            "Rate",
            "Cost",
        ]

    def get_value(self, field: str):
        """Returns value for a field.

        :param field: Field to return.
        """
        return getattr(self, field)

    def get_values(self):
        return [
            self.get_value(field.name) for field in dataclasses.fields(self)
        ]


def datetime_type(v):
    return pytz.utc.localize(datetime.strptime(v, '%Y-%m-%d'))


class Command(BaseCommand):
    help = "Generate invoices for storage billing."

    def add_arguments(self, parser):
        parser.add_argument('--start', type=datetime_type,
                            default=self.default_start_argument(),
                            help='Start period for billing.')
        parser.add_argument('--end', type=datetime_type,
                            default=self.default_end_argument(),
                            help='End period for billing.')
        parser.add_argument(
            '--invoice-month', type=str,
            default=self.default_start_argument().strftime('%Y-%m')
        )
        parser.add_argument('--output', type=str, default='invoices.csv',
                             help='CSV file to write invoices to.')
        parser.add_argument('--openstack-gb-rate', type=Decimal, required=True,
                            help='Rate for OpenStack Volume and Object GB/hour.')
        parser.add_argument('--openshift-gb-rate', type=Decimal, required=True,
                            help='Rate for OpenShift GB/hour.')
        parser.add_argument('--s3-endpoint-url', type=str,
                            default='https://s3.us-east-005.backblazeb2.com')
        parser.add_argument('--s3-bucket-name', type=str,
                            default='nerc-invoicing')
        parser.add_option('--upload-to-s3',
                          help='Upload generated CSV invoice to S3 storage.')

    @staticmethod
    def default_start_argument():
        d = (datetime.today() - timedelta(days=1)).replace(day=1)
        d = d.replace(hour=0, minute=0, second=0, microsecond=0)
        return d

    @staticmethod
    def default_end_argument():
        d = datetime.today()
        d = d.replace(hour=0, minute=0, second=0, microsecond=0)
        return d

    @staticmethod
    def upload_to_s3(s3_endpoint, s3_bucket, file_location, invoice_month):
        s3_key_id = os.getenv("S3_OUTPUT_ACCESS_KEY_ID")
        s3_secret = os.getenv("S3_OUTPUT_SECRET_ACCESS_KEY")

        if not s3_key_id or not s3_secret:
            raise Exception("Must provide S3_OUTPUT_ACCESS_KEY_ID and"
                            " S3_OUTPUT_SECRET_ACCESS_KEY environment variables.")
        if not invoice_month:
            raise Exception("No invoice month specified. Required for S3 upload.")

        s3 = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_key_id,
            aws_secret_access_key=s3_secret,
        )

        primary_location = (
            f"Invoices/{invoice_month}/"
            f"Service Invoices/NERC Storage {invoice_month}.csv"
        )
        s3.upload_file(file_location, Bucket=s3_bucket, Key=primary_location)
        logger.info(f"Uploaded to {primary_location}.")

        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        secondary_location = (
            f"Invoices/{invoice_month}/"
            f"Archive/NERC Storage {invoice_month} {timestamp}.csv"
        )
        s3.upload_file(file_location, Bucket=s3_bucket, Key=secondary_location)
        logger.info(f"Uploaded to {secondary_location}.")

    def handle(self, *args, **options):
        def process_invoice_row(allocation, attributes, su_name, rate):
            """Calculate the value and write the bill using the writer."""
            time = 0
            for attribute in attributes:
                time += utils.calculate_quota_unit_hours(
                    allocation, attribute, options['start'], options['end']
                )
            if time > 0:
                row = InvoiceRow(
                    InvoiceMonth=options['invoice_month'],
                    Project_Name=allocation.get_attribute(attributes.ALLOCATION_PROJECT_NAME),
                    Project_ID=allocation.get_attribute(attributes.ALLOCATION_PROJECT_ID),
                    PI=allocation.project.pi,
                    Invoice_Type_Hours=time,
                    Invoice_Type=su_name,
                    Rate=rate,
                    Cost=time * rate
                )
                csv_invoice_writer.writerow(
                    row.get_values()
                )

        logger.info(f'Processing invoices for {options["invoice_month"]}.')
        logger.info(f'Interval {options["start"] - options["end"]}.')

        openstack_resources = Resource.objects.filter(
            resource_type=ResourceType.objects.get(
                name='OpenStack'
            )
        )
        openstack_allocations = Allocation.objects.filter(
            resources__in=openstack_resources
        )
        openshift_resources = Resource.objects.filter(
            resource_type=ResourceType.objects.get(
                name='OpenShift'
            )
        )
        openshift_allocations = Allocation.objects.filter(
            resources__in=openshift_resources
        )

        logger.info(f'Writing to {options["output"]}.')
        with open(options['output'], 'w', newline='') as f:
            csv_invoice_writer = csv.writer(
                f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL
            )
            # Write Headers
            csv_invoice_writer.writerow(InvoiceRow.get_headers())

            for allocation in openstack_allocations:
                allocation_str = f'{allocation.pk} of project "{allocation.project.title}"'
                msg = f'Starting billing for for allocation {allocation_str}.'
                logger.debug(msg)

                process_invoice_row(
                    allocation,
                    [attributes.QUOTA_VOLUMES_GB, attributes.QUOTA_OBJECT_GB],
                    "OpenStack Storage",
                    options['openstack_gb_rate'])

            for allocation in openshift_allocations:
                allocation_str = f'{allocation.pk} of project "{allocation.project.title}"'
                msg = f'Starting billing for for allocation {allocation_str}.'
                logger.debug(msg)

                process_invoice_row(
                    allocation,
                    [attributes.QUOTA_LIMITS_EPHEMERAL_STORAGE_GB, attributes.QUOTA_REQUESTS_STORAGE],
                    "OpenShift Storage",
                    options['openshift_gb_rate']
                )

        if options['upload_to_s3']:
            logger.info(f'Uploading to S3 endpoint {options['s3_endpoint_url']}.')
            self.upload_to_s3(options['s3_endpoint_url'],
                              options['s3_bucket'],
                              options['output'],
                              options['invoice_month'])
