from unittest import mock

import kubernetes.dynamic.exceptions as kexc

from coldfront_plugin_cloud.tests import base
from coldfront_plugin_cloud import openshift
from coldfront_plugin_cloud.openshift import OpenShiftResourceAllocator


class TestMocOpenShiftRBAC(base.TestBase):
    def setUp(self) -> None:
        mock_resource = mock.Mock()
        mock_allocation = mock.Mock()
        self.allocator = OpenShiftResourceAllocator(mock_resource, mock_allocation)
        self.allocator.id_provider = "fake_idp"
        self.allocator.k8_client = mock.Mock()
        self.allocator.member_role_name = "admin"

    def test_subject_in_rolebindings_false(self):
        fake_rb = {
            "subjects": [
                {
                    "kind": "User",
                    "name": "fake-user-2",
                }
            ]
        }
        output = self.allocator._subject_in_rolebinding("User", "fake-user", fake_rb)
        self.assertFalse(output)

    def test_subject_in_rolebindings_true(self):
        fake_rb = {
            "subjects": [
                {
                    "kind": "User",
                    "name": "fake-user",
                }
            ]
        }
        output = self.allocator._subject_in_rolebinding("User", "fake-user", fake_rb)
        self.assertTrue(output)

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_rolebindings"
    )
    def test_add_user_to_role(
        self, fake_update_rb, fake_get_rb, fake_update_group, fake_get_group
    ):
        fake_get_group.return_value = {
            "users": [],
        }
        fake_get_rb.return_value = {
            "subjects": [{"kind": "Group", "name": "fake-project-users"}],
        }
        self.allocator.assign_role_on_user("fake-user", "fake-project")
        fake_update_group.assert_called_with(
            "fake-project-users",
            {"users": ["fake-user"]},
        )
        fake_update_rb.assert_not_called()

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_rolebindings"
    )
    def test_add_user_to_role_adds_group_subject(
        self, fake_update_rb, fake_get_rb, fake_update_group, fake_get_group
    ):
        fake_get_group.return_value = {
            "users": [],
        }
        fake_get_rb.return_value = {
            "subjects": [],
        }
        self.allocator.assign_role_on_user("fake-user", "fake-project")
        fake_update_group.assert_called_with(
            "fake-project-users",
            {"users": ["fake-user"]},
        )
        fake_update_rb.assert_called_with(
            "fake-project",
            {"subjects": [{"kind": "Group", "name": "fake-project-users"}]},
        )

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_create_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_rolebindings"
    )
    def test_add_user_to_role_group_not_exists(
        self, fake_update_rb, fake_get_rb, fake_create_group, fake_get_group
    ):
        fake_error = kexc.NotFoundError(mock.Mock())
        fake_get_group.side_effect = fake_error
        fake_get_rb.return_value = {
            "subjects": [{"kind": "Group", "name": "fake-project-users"}],
        }
        self.allocator.assign_role_on_user("fake-user", "fake-project")
        fake_create_group.assert_called_with("fake-project-users", users=["fake-user"])
        fake_update_rb.assert_not_called()

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_create_rolebindings"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    def test_add_user_to_role_not_exists(
        self, fake_get_rb, fake_create_rb, fake_get_group
    ):
        fake_get_group.return_value = {"users": ["fake-user"]}
        fake_error = kexc.NotFoundError(mock.Mock())
        fake_get_rb.side_effect = fake_error
        self.allocator.assign_role_on_user("fake-user", "fake-project")
        fake_create_rb.assert_called_with(
            "fake-project", "fake-project-users", "admin", subject_kind="Group"
        )

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_group"
    )
    def test_remove_user_from_role(self, fake_update_group, fake_get_group):
        fake_get_group.return_value = {
            "users": ["fake-user"],
        }
        self.allocator.remove_role_from_user("fake-user", "fake-project")
        fake_update_group.assert_called_with(
            "fake-project-users",
            {"users": []},
        )

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_update_group"
    )
    def test_remove_user_from_role_not_exists(self, fake_update_group, fake_get_group):
        fake_get_group.side_effect = kexc.NotFoundError(mock.Mock())
        self.allocator.remove_role_from_user("fake-user", "fake-project")
        fake_update_group.assert_not_called()

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    def test_get_users(self, fake_get_group):
        fake_get_group.return_value = {"users": ["user1", "user2"]}
        self.assertEqual(self.allocator.get_users("fake-project"), {"user1", "user2"})

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    def test_get_users_group_missing(self, fake_get_group):
        fake_get_group.side_effect = kexc.NotFoundError(mock.Mock())
        self.assertEqual(self.allocator.get_users("fake-project"), set())

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    def test_get_role(self, fake_get_rolebindings, fake_get_group):
        fake_get_rolebindings.return_value = {
            "subjects": [{"kind": "Group", "name": "fake-project-users"}],
        }
        fake_get_group.return_value = {"users": ["fake-user"]}
        self.allocator._get_role("fake-user", "fake-project")
        fake_get_rolebindings.assert_called_with("fake-project", "admin")
        fake_get_group.assert_called_with("fake-project-users")

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    def test_get_role_group_has_no_rolebinding(self, fake_get_rolebindings, fake_get_group):
        fake_get_rolebindings.return_value = {
            "subjects": [{"kind": "Group", "name": "another-group"}],
        }
        fake_get_group.return_value = {"users": ["fake-user"]}
        with self.assertRaises(openshift.NotFound):
            self.allocator._get_role("fake-user", "fake-project")

    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_group"
    )
    @mock.patch(
        "coldfront_plugin_cloud.openshift.OpenShiftResourceAllocator._openshift_get_rolebindings"
    )
    def test_get_role_user_not_in_group(self, fake_get_rolebindings, fake_get_group):
        fake_get_rolebindings.return_value = {
            "subjects": [{"kind": "Group", "name": "fake-project-users"}],
        }
        fake_get_group.return_value = {"users": []}
        with self.assertRaises(openshift.NotFound):
            self.allocator._get_role("fake-user", "fake-project")

    def test_get_rolebindings(self):
        fake_rb = mock.Mock(spec=["to_dict"])
        fake_rb.to_dict.return_value = {"subjects": []}
        self.allocator.k8_client.resources.get.return_value.get.return_value = fake_rb
        res = self.allocator._openshift_get_rolebindings("fake-project", "admin")
        self.assertEqual(res, fake_rb.to_dict())

    def test_get_rolebindings_no_subjects(self):
        fake_rb = mock.Mock(spec=["to_dict"])
        fake_rb.to_dict.return_value = {}
        self.allocator.k8_client.resources.get.return_value.get.return_value = fake_rb
        res = self.allocator._openshift_get_rolebindings("fake-project", "admin")
        self.assertEqual(res, {"subjects": []})

    def test_list_rolebindings(self):
        fake_rb = mock.Mock(spec=["to_dict"])
        fake_rb.to_dict.return_value = {
            "items": ["rb1", "rb2"],
        }
        self.allocator.k8_client.resources.get.return_value.get.return_value = fake_rb
        res = self.allocator._openshift_list_rolebindings("fake-project")
        self.assertEqual(res, ["rb1", "rb2"])

    def test_list_rolebindings_not_exists(self):
        fake_error = kexc.NotFoundError(mock.Mock())
        self.allocator.k8_client.resources.get.return_value.get.side_effect = fake_error
        res = self.allocator._openshift_list_rolebindings("fake-project")
        self.assertEqual(res, [])

    def test_create_rolebindings(self):
        fake_rb = mock.Mock(spec=["to_dict"])
        fake_rb.to_dict.return_value = {}
        self.allocator.k8_client.resources.get.return_value.create.return_value = (
            fake_rb
        )
        res = self.allocator._openshift_create_rolebindings(
            "fake-project", "fake-user", "admin"
        )
        self.assertEqual(res, {})
        self.allocator.k8_client.resources.get.return_value.create.assert_called_with(
            namespace="fake-project",
            body={
                "metadata": {"name": "admin", "namespace": "fake-project"},
                "subjects": [{"name": "fake-user", "kind": "User"}],
                "roleRef": {"name": "admin", "kind": "ClusterRole"},
            },
        )

    def test_create_rolebindings_group(self):
        fake_rb = mock.Mock(spec=["to_dict"])
        fake_rb.to_dict.return_value = {}
        self.allocator.k8_client.resources.get.return_value.create.return_value = (
            fake_rb
        )
        res = self.allocator._openshift_create_rolebindings(
            "fake-project", "fake-project-users", "admin", subject_kind="Group"
        )
        self.assertEqual(res, {})
        self.allocator.k8_client.resources.get.return_value.create.assert_called_with(
            namespace="fake-project",
            body={
                "metadata": {"name": "admin", "namespace": "fake-project"},
                "subjects": [{"name": "fake-project-users", "kind": "Group"}],
                "roleRef": {"name": "admin", "kind": "ClusterRole"},
            },
        )
