""" Tests for the config generator """

from unittest.mock import patch, call, mock_open
import unittest

from cloud_info_catchall.config_generator import ShareDiscovery
from fedcloudclient.endpoint import TokenException


class TestConfig(unittest.TestCase):
    @patch(
        "cloud_info_provider.auth_refreshers.oidc_refresh.OidcRefreshToken._refresh_token"
    )
    def test_token_refresh(self, m):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
        t = d.refresh_token(
            {"client_id": "id", "client_secret": "secret", "refresh_token": "token"}
        )
        m.assert_called_with(
            "https://aai.egi.eu",
            "id",
            "secret",
            "token",
            "openid email profile voperson_id eduperson_entitlement",
        )
        self.assertEqual(t, m.return_value)

    @patch("fedcloudclient.endpoint.retrieve_unscoped_token")
    def test_failed_token_shares(self, m):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
        m.side_effect = TokenException()
        s = d.get_token_shares("foobar")
        m.assert_called_with("https://openstack.org", "foobar", "oidc")
        self.assertEqual(s, {})

    @patch("fedcloudclient.endpoint.get_projects_from_single_site")
    @patch("fedcloudclient.endpoint.retrieve_unscoped_token")
    def test_token_shares(self, m_token, m_proj):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
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
        s = d.get_token_shares("foobar")
        m_token.assert_called_with("https://openstack.org", "foobar", "oidc")
        m_proj.assert_called_with("https://openstack.org", m_token.return_value)
        # return only the enabled with VO
        self.assertEqual(s, {"foobar.eu": {"auth": {"project_id": "id1"}}})

    @patch.object(ShareDiscovery, "refresh_token")
    @patch.object(ShareDiscovery, "get_token_shares")
    @patch("os.makedirs")
    def test_generate_shares(self, m_makedirs, m_shares, m_refresh):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
        secrets = {
            "client_id": "bar",
            "client_secret": "foo",
            "refresh_token": "foobar",
        }
        secrets2 = {
            "client_id": "barz",
            "client_secret": "fooz",
            "refresh_token": "foobarz",
        }
        m_shares.side_effect = [
            {"foobar.eu": {"auth": {"project_id": "id1"}}},
            {"baz.eu": {"auth": {"project_id": "id2"}}},
        ]
        with patch("builtins.open", mock_open()) as mock_file:
            s = d.generate_shares({"s1": secrets, "s2": secrets2})
        m_refresh.assert_has_calls([call(secrets), call(secrets2)])
        m_shares.assert_called_with(m_refresh.return_value)
        m_makedirs.assert_has_calls(
            [call("vo/foobar.eu", exist_ok=True), call("vo/baz.eu", exist_ok=True)]
        )
        self.assertEqual(
            s,
            {
                "foobar.eu": {"auth": {"project_id": "id1"}},
                "baz.eu": {"auth": {"project_id": "id2"}},
            },
        )

    def test_generate_empty_shares(self):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
        with self.assertRaises(Exception):
            d.generate_shares({})

    @patch.object(ShareDiscovery, "generate_shares")
    def test_generate_config(self, m):
        d = ShareDiscovery(
            "https://openstack.org", "egi.eu", "oidc", "https://aai.egi.eu", "vo"
        )
        s = d.generate_config("site", {})
        m.assert_called_with({})
        self.assertEqual(
            s, {"site": {"name": "site"}, "compute": {"shares": m.return_value}}
        )


if __name__ == "__main__":
    unittest.main()
