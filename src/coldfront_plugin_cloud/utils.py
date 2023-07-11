import datetime
import math
import pytz
import re
import secrets

from coldfront.core.allocation.models import (AllocationAttribute,
                                              AllocationAttributeType)


def env_safe_name(name):
    return name.replace(' ', '_').replace('-', '_').upper()


def set_attribute_on_allocation(allocation, attribute_type, attribute_value):
    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
        name=attribute_type)
    try:
        attribute_obj = AllocationAttribute.objects.get(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation
        )
        attribute_obj.value = attribute_value
        attribute_obj.save()
    except AllocationAttribute.DoesNotExist:
        AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation,
            value=attribute_value,
        )

def get_unique_project_name(project_name, max_length=None):
    # The random hex at the end of the project name is 6 chars, 1 hyphen
    max_without_suffix = max_length - 7 if max_length else None
    return f'{project_name[:max_without_suffix]}-f{secrets.token_hex(3)}'

def get_sanitized_project_name(project_name):
    '''
    Returns a sanitized project name that only contains lowercase
    alphanumeric characters and dashes (not leading or trailing.)
    '''
    project_name = project_name.lower()

    # replace special characters with dashes
    project_name = re.sub('[^a-z0-9-]', '-', project_name)

    # remove repeated and trailing dashes
    project_name = re.sub('-+', '-', project_name).strip('-')
    return project_name


def calculate_quota_unit_hours(allocation, attribute, start, end):
    """Returns unit*hours of quota allocated in a given period.

    Calculation is rounded up by the hour and tracks the history of change
    requests.

    :param attribute: Name of the attribute to calculate.
    :param start: Start time to being calculation.
    :param end: Optional. End time for calculation.
    :return: Value of attribute * amount of hours.
    """
    allocation_attribute = AllocationAttribute.objects.filter(
        allocation_attribute_type__name=attribute,
        allocation = allocation
    ).first()
    if allocation_attribute is None:
        return 0
    value_history = list(allocation_attribute.history.all())
    value_history.reverse()

    value_times_seconds = 0
    last_event_time = start
    last_event_value = 0
    for event in value_history:
        event_time = event.modified

        if event_time < start:
            event_time = start

        if end and event_time > end:
           event_time = end

        seconds_since_last_event = math.ceil((event_time - last_event_time).total_seconds())
        value_times_seconds += seconds_since_last_event * last_event_value

        last_event_time = event_time
        last_event_value = int(event.value)

    since_last_event = math.ceil((end - last_event_time).total_seconds())
    value_times_seconds += since_last_event * last_event_value

    return math.ceil(value_times_seconds / 3600)
