"""Tests for the discovery"""

import copy
import unittest
from unittest.mock import MagicMock, mock_open, patch

import httpx
import respx
import testtools
from oslo_config import fixture

from . import discovery as disco

SAMPLE_SITE = """
---
gocdb: TEST
endpoint: https://example.com:5000/v3
images:
  sync: true
  formats:
    - qcow2
    - raw
vos:
  - name: ops
    auth:
      somekey: "value"
  - name: fake-vo.example.com
"""

SITES_INFO = [
    {
        "id": "1",
        "name": "TEST",
        "url": "https://example.com:5000/v3",
        "state": "",
        "hostname": "example.com",
        "projects": [
            {"id": "abc", "name": "ops"},
            {
                "id": "def",
                "name": "fake-vo.example.com",
            },
        ],
        "shares": {
            "ops": {"id": "abc", "name": "ops"},
            "fake-vo.example.com": {
                "id": "def",
                "name": "fake-vo.example.com",
            },
        },
    },
]


class TestDiscovery(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    @respx.mock
    def test_fetch_site_info_ok(self):
        sample_sites = {}
        self.conf.set_override(
            "fedcloud_info_system_url", "https://example.com", group="discovery"
        )
        route = respx.get("https://example.com/sites/").mock(
            return_value=httpx.Response(200, json=sample_sites)
        )
        sites = disco.fetch_site_info()
        assert sites == {}
        assert route.called

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("glob.iglob")
    def test_load_sites(self, m_glob, m_fetch):
        m_fetch.return_value = SITES_INFO
        m_glob.return_value = ["file1.yaml"]
        with patch("builtins.open", mock_open(read_data=SAMPLE_SITE)):
            sites = disco.load_sites()
            assert sites == {
                "1": {
                    "hostname": "example.com",
                    "id": "1",
                    "name": "TEST",
                    "projects": [
                        {
                            "id": "abc",
                            "name": "ops",
                        },
                        {
                            "id": "def",
                            "name": "fake-vo.example.com",
                        },
                    ],
                    "shares": {
                        "fake-vo.example.com": {
                            "auth": {},
                            "id": "def",
                            "name": "fake-vo.example.com",
                        },
                        "ops": {
                            "auth": {
                                "somekey": "value",
                            },
                            "id": "abc",
                            "name": "ops",
                        },
                    },
                    "state": "",
                    "static": {
                        "endpoint": "https://example.com:5000/v3",
                        "gocdb": "TEST",
                        "images": {
                            "formats": [
                                "qcow2",
                                "raw",
                            ],
                            "sync": True,
                        },
                        "vos": [
                            {
                                "auth": {
                                    "somekey": "value",
                                },
                                "name": "ops",
                            },
                            {
                                "name": "fake-vo.example.com",
                            },
                        ],
                    },
                    "url": "https://example.com:5000/v3",
                },
            }

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("glob.iglob")
    def test_load_non_static_site(self, m_glob, m_fetch):
        foo_site = copy.deepcopy(SITES_INFO)
        foo_site[0]["name"] = "foo"
        m_fetch.return_value = foo_site
        m_glob.return_value = ["file1.yaml"]
        with patch("builtins.open", mock_open(read_data=SAMPLE_SITE)):
            sites = disco.load_sites()
            assert sites == {}

    @patch("jwt.decode")
    @patch("hvac.Client")
    def test_get_vo_secrets(self, m_hvac, m_decode):
        m_client = MagicMock()
        m_hvac.return_value = m_client
        m_client.auth.jwt.jwt_login.return_value = None
        m_client.secrets.kv.v1.read_secret.return_value = {
            "data": {
                "username": "demo",
                "password": "1234",
            }
        }
        m_decode.return_value = {"sub": "user@egi.eu"}
        r = disco.get_vo_secrets(
            "https://example.com:5000/v3", "ops", "the_access_token"
        )
        assert r == {"password": "1234", "username": "demo"}
        m_hvac.assert_called_once()
        m_client.auth.jwt.jwt_login.assert_called_with(role="", jwt="the_access_token")
        m_client.secrets.kv.v1.read_secret.assert_called_with(
            path="users/user@egi.eu/cloudmon/example.com/ops",
            mount_point="/secrets/",
        )


if __name__ == "__main__":
    unittest.main()
