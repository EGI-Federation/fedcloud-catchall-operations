"""Tests for the Share discovery"""

import unittest
from unittest.mock import MagicMock, call, mock_open, patch

import responses
from cloud_info_catchall.share_discovery import (
    AccessTokenShareDiscovery,
    RefresherShareDiscovery,
    ShareDiscovery,
)
from keystoneauth1.exceptions.base import ClientException
from responses import matchers


class ShareDiscoveryTest(unittest.TestCase):
    DISCOVERER_CLASS = ShareDiscovery
    CONFIG = {
        "auth_url": "https://openstack.org",
        "identity_provider": "egi.eu",
        "protocol": "oidc",
        "token_url": "https://aai.egi.eu",
        "vo_dir": "vo",
        "vo_fallback": {"123": "cloud.egi.eu"},
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

    def test_get_project_no_vo_property_fallback(self):
        p = {
            "enabled": True,
            "name": "baz",
            "id": "123",
        }
        self.assertEqual(self.discoverer.get_project_vos(p), ["cloud.egi.eu"])

    def test_get_project_multiple_vo_property(self):
        p = {"enabled": True, "name": "foo.eu", "egi.VO": "foo,bar"}
        self.assertEqual(self.discoverer.get_project_vos(p), ["foo", "bar"])

    @patch("keystoneclient.v3.auth.AuthManager.projects")
    def test_token_shares(self, m_auth_manager):
        class mock_p:
            def __init__(self, d):
                self.d = d

            def to_dict(self):
                return self.d

        m_get_token = MagicMock()
        self.discoverer.get_token = m_get_token
        m_build_share = MagicMock()
        self.discoverer.build_share = m_build_share
        m_auth_manager.return_value = [
            mock_p(
                {
                    "VO": "foobar.eu",
                    "id": "id1",
                    "name": "enabled foobar VO",
                    "enabled": True,
                }
            ),
            mock_p(
                {
                    "VO": "disabled.eu",
                    "id": "id2",
                    "name": "disabled VO",
                    "enabled": False,
                }
            ),
            mock_p({"id": "id3", "name": "not VO project", "enabled": True}),
        ]
        s = self.discoverer.get_token_shares()
        m_get_token.assert_called_with()
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

    @patch("keystoneclient.v3.auth.AuthManager.projects")
    def test_failed_token_shares(self, m_projects):
        m_get_token = MagicMock()
        self.discoverer.get_token = m_get_token
        m_projects.side_effect = ClientException()
        s = self.discoverer.get_token_shares()
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

    @responses.activate
    def test_token_refresh(self):
        responses.post(
            "https://aai.egi.eu",
            match=[
                matchers.urlencoded_params_matcher(
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": "token",
                        "scope": "openid email profile voperson_id eduperson_entitlement",
                        "client_secret": "secret",
                    },
                )
            ],
            json={"access_token": "foo"},
        )
        t = self.discoverer.get_token()
        self.assertEqual(t, "foo")

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
