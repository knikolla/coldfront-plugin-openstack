import datetime
from unittest import mock
from os import devnull
import pytz
import sys

import freezegun

from coldfront_plugin_cloud import attributes
from coldfront_plugin_cloud.tests import base
from coldfront_plugin_cloud.management.commands import register_cloud_attributes
from coldfront_plugin_cloud import utils

from coldfront.core.resource import models as resource_models
from coldfront.core.allocation import models as allocation_models

from django.core.management import call_command


class TestCalculateAllocationQuotaHours(base.TestBase):
    def test_new_allocation_quota(self):
        self.resource = self.new_openshift_resource(
            name="",
            auth_url="",
        )
        user = self.new_user()
        project = self.new_project(pi=user)
        allocation = self.new_allocation(project, self.resource, 2)

        with freezegun.freeze_time("2020-03-15 00:01:00"):
            utils.set_attribute_on_allocation(
                allocation, attributes.QUOTA_LIMITS_EPHEMERAL_STORAGE_GB, 2)

        with freezegun.freeze_time("2020-03-16 23:59:00"):
            utils.set_attribute_on_allocation(
                allocation, attributes.QUOTA_LIMITS_EPHEMERAL_STORAGE_GB, 0)

        allocation.refresh_from_db()

        value = utils.calculate_quota_unit_hours(
            allocation,
            attributes.QUOTA_LIMITS_EPHEMERAL_STORAGE_GB,
            pytz.utc.localize(datetime.datetime(2020, 3, 1, 0, 0, 1)),
            pytz.utc.localize(datetime.datetime(2020, 3, 31, 23, 59, 59))
        )
        self.assertEqual(value, 96)

