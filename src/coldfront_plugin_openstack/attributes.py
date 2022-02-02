RESOURCE_AUTH_URL = 'OpenStack Auth URL'
RESOURCE_FEDERATION_PROTOCOL = 'OpenStack Federation Protocol'
RESOURCE_IDP = 'OpenStack Identity Provider'
RESOURCE_PROJECT_DOMAIN = 'OpenStack Domain for Projects'
RESOURCE_ROLE = 'OpenStack Role for User in Project'
RESOURCE_USER_DOMAIN = 'OpenStack Domain for Users'

RESOURCE_SUPPORTS_FED_ATTR = 'OpenStack Identity supports federated create'

RESOURCE_ATTRIBUTES_TEXT = [RESOURCE_AUTH_URL,
                            RESOURCE_FEDERATION_PROTOCOL,
                            RESOURCE_IDP,
                            RESOURCE_PROJECT_DOMAIN,
                            RESOURCE_ROLE,
                            RESOURCE_USER_DOMAIN]
RESOURCE_ATTRIBUTES_BOOL = [RESOURCE_SUPPORTS_FED_ATTR]


ALLOCATION_PROJECT_ID = 'OpenStack Project ID'
ALLOCATION_PROJECT_NAME = 'OpenStack Project Name'

ALLOCATION_ATTRIBUTES = [ALLOCATION_PROJECT_ID,
                         ALLOCATION_PROJECT_NAME]

QUOTA_INSTANCES = 'OpenStack Compute Instance Quota'
QUOTA_RAM = 'OpenStack Compute RAM Quota'
QUOTA_VCPU = 'OpenStack Compute vCPU Quota'

QUOTA_VOLUMES = 'OpenStack Volume Quota'
QUOTA_VOLUMES_GB = 'OpenStack Volume GB Quota'

ALLOCATION_QUOTA_ATTRIBUTES = [QUOTA_INSTANCES,
                               QUOTA_RAM,
                               QUOTA_VCPU,
                               QUOTA_VOLUMES,
                               QUOTA_VOLUMES_GB]

