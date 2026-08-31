from unittest import mock

from coldfront_plugin_cloud.tests.unit.openshift import base
from coldfront_plugin_cloud.openshift import PROJECT_DEFAULT_LABELS


class TestOpenshiftQuota(base.TestUnitOpenshiftBase):
    def test_get_project(self):
        fake_project = mock.Mock(spec=["to_dict"])
        fake_project.to_dict.return_value = {"project": "fake-project"}
        self.allocator.k8_client.resources.get.return_value.get.return_value = (
            fake_project
        )
        res = self.allocator._get_project("fake-project")
        assert res == {"project": "fake-project"}

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_create_limits",
        mock.Mock(),
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_create_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_create_rolebindings"
    )
    def test_create_project(self, fake_create_rolebinding, fake_create_group):
        self.allocator.allocation.project.pi.username = "fake-user"
        self.allocator.allocation.project_id = "Fake Project ID"
        self.allocator.member_role_name = "admin"
        self.allocator._create_project("fake-project-name", "Fake Project ID")
        self.allocator.k8_client.resources.get.return_value.create.assert_called_with(
            body={
                "metadata": {
                    "name": "fake-project-name",
                    "annotations": {
                        "cf_project_id": "Fake Project ID",
                        "cf_pi": "fake-user",
                        "openshift.io/display-name": "fake-project-name",
                        "openshift.io/requester": "fake-user",
                    },
                    "labels": PROJECT_DEFAULT_LABELS,
                }
            }
        )
        fake_create_group.assert_called_with("Fake Project ID-users")
        fake_create_rolebinding.assert_called_with(
            "fake-project-name", "Fake Project ID-users", "admin", subject_kind="Group"
        )

    def test_delete_project(self):
        self.allocator.disable_project("fake-project")
        self.allocator.k8_client.resources.get.return_value.delete.assert_called_with(
            name="fake-project"
        )
