""" Tests for the Share discovery """

import unittest
from unittest.mock import MagicMock, call, mock_open, patch

from cloud_info_catchall.share_discovery import (
    AccessTokenShareDiscovery,
    RefresherShareDiscovery,
    ShareDiscovery,
)
from fedcloudclient.endpoint import TokenException


class ShareDiscoveryTest(unittest.TestCase):
    DISCOVERER_CLASS = ShareDiscovery
    CONFIG = {
        "auth_url": "https://openstack.org",
        "identity_provider": "egi.eu",
        "protocol": "oidc",
        "token_url": "https://aai.egi.eu",
        "vo_dir": "vo",
    }
    SECRET = {"foo": "bar"}

    def setUp(self):
        self.discoverer = self.DISCOVERER_CLASS(self.CONFIG, self.SECRET)

    def test_get_project_vo_disabled(self):
        p = {
            "enabled": False,
            "name": "foo.eu",
            "VO": "foo",
        }
        self.assertEqual(self.discoverer.get_project_vos(p), [])

    def test_get_project_vo_egi_property(self):
        p = {
            "enabled": True,
            "name": "foo.eu",
            "VO": "bar",
            "egi.VO": "foo",
        }
        self.assertEqual(self.discoverer.get_project_vos(p), ["foo"])

    def test_get_project_vo_property(self):
        p = {
            "enabled": True,
            "name": "foo.eu",
            "VO": "bar",
        }
        self.assertEqual(self.discoverer.get_project_vos(p), ["bar"])

    def test_get_project_no_vo_property(self):
        p = {
            "enabled": True,
            "name": "foo.eu",
        }
        self.assertEqual(self.discoverer.get_project_vos(p), [])

    def test_get_project_multiple_vo_property(self):
        p = {"enabled": True, "name": "foo.eu", "egi.VO": "foo,bar"}
        self.assertEqual(self.discoverer.get_project_vos(p), ["foo", "bar"])

    @patch("fedcloudclient.endpoint.get_projects_from_single_site")
    @patch("fedcloudclient.endpoint.retrieve_unscoped_token")
    def test_token_shares(self, m_fedcli_token, m_proj):
        m_get_token = MagicMock()
        self.discoverer.get_token = m_get_token
        m_build_share = MagicMock()
        self.discoverer.build_share = m_build_share
        m_proj.return_value = [
            {
                "VO": "foobar.eu",
                "id": "id1",
                "name": "enabled foobar VO",
                "enabled": True,
            },
            {"VO": "disabled.eu", "id": "id2", "name": "disabled VO", "enabled": False},
            {"id": "id3", "name": "not VO project", "enabled": True},
        ]
        s = self.discoverer.get_token_shares()
        m_fedcli_token.assert_called_with(
            "https://openstack.org", m_get_token.return_value, "oidc"
        )
        m_get_token.assert_called_with()
        m_proj.assert_called_with("https://openstack.org", m_fedcli_token.return_value)
        m_build_share.assert_called_with(
            {
                "VO": "foobar.eu",
                "id": "id1",
                "name": "enabled foobar VO",
                "enabled": True,
            },
            m_get_token.return_value,
        )
        # return only the enabled with VO
        self.assertEqual(s, {"foobar.eu": m_build_share.return_value})

    @patch("fedcloudclient.endpoint.retrieve_unscoped_token")
    def test_failed_token_shares(self, m_fedcli_token):
        m_get_token = MagicMock()
        self.discoverer.get_token = m_get_token
        m_fedcli_token.side_effect = TokenException()
        s = self.discoverer.get_token_shares()
        m_fedcli_token.assert_called_with(
            "https://openstack.org", m_get_token.return_value, "oidc"
        )
        self.assertEqual(s, {})

    def test_build_share(self):
        project = {"id": "foobar"}
        self.assertEqual(
            self.discoverer.build_share(project, "token"),
            {"auth": {"project_id": "foobar"}},
        )


class TestRefresherShareDiscovery(ShareDiscoveryTest):
    SECRET = {"client_id": "id", "client_secret": "secret", "refresh_token": "token"}
    DISCOVERER_CLASS = RefresherShareDiscovery

    @patch(
        "cloud_info_provider.auth_refreshers.oidc_refresh.OidcRefreshToken._refresh_token"
    )
    def test_token_refresh(self, m):
        t = self.discoverer.get_token()
        m.assert_called_with(
            "https://aai.egi.eu",
            "id",
            "secret",
            "token",
            "openid email profile voperson_id eduperson_entitlement",
        )
        self.assertEqual(t, m.return_value)

    @patch("os.makedirs")
    def config_shares(self, m_makedirs):
        shares = [
            {"foobar.eu": {"auth": {"project_id": "id1"}}},
            {"baz.eu": {"auth": {"project_id": "id2"}}},
        ]
        with patch("builtins.open", mock_open()) as m_file:
            self.discoverer.config_shares(shares, "token")
        handle = m_file()
        for vo in shares:
            for field in self.SECRET:
                m_file.assert_any_call(f"vo/{vo}/{field}", "w+"),
                handle.write.assert_any_call(self.SECRET[field])
        m_makedirs.assert_has_calls(
            [call("vo/foobar.eu", exist_ok=True), call("vo/baz.eu", exist_ok=True)]
        )


class TestAccessTokenShareDiscovery(ShareDiscoveryTest):
    DISCOVERER_CLASS = AccessTokenShareDiscovery
    SECRET = {"access_token": "token"}

    def test_get_token(self):
        self.assertEqual(self.discoverer.get_token(), "token")

    def test_build_share(self):
        project = {"id": "foobar"}
        self.assertEqual(
            self.discoverer.build_share(project, "token"),
            {"auth": {"project_id": "foobar"}},
        )


if __name__ == "__main__":
    unittest.main()
