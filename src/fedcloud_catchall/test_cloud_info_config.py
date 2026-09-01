"""Tests for the discovery"""

from unittest.mock import mock_open, patch

import testtools
from oslo_config import fixture

from .cloud_info_config import auditor_config, configure, read_site_config, secretize

app_cred_site_yaml = """
---
gocdb: TEST
endpoint: https://example.com:5000/v3
auth: v3applicationcredential
vos:
  - name: ops
    auth:
      foo: bar
"""

app_cred_site = {
    "gocdb": "TEST",
    "endpoint": "https://example.com:5000/v3",
    "auth": "v3applicationcredential",
    "vos": [
        {
            "name": "ops",
            "auth": {
                "foo": "bar",
            },
        },
    ],
}
regular_site = {
    "gocdb": "TEST",
    "endpoint": "https://example.com:5000/v3",
    "vos": [
        {
            "auth": {
                "foo": "bar",
            },
            "name": "ops",
        },
    ],
}


class TestCloudConfig(testtools.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    def test_read_site_config(self):
        with patch("builtins.open", mock_open(read_data=app_cred_site_yaml)):
            r = read_site_config("site_config_file")
        assert r == app_cred_site

    @patch("fedcloud_catchall.cloud_info_config.get_vo_secrets")
    def test_secretize_app_cred_site(self, m_get_secrets):
        m_get_secrets.return_value = {
            "username": "demo",
            "password": "1234",
        }
        r = secretize(app_cred_site, "the_access_token")
        assert r == {
            "gocdb": "TEST",
            "endpoint": "https://example.com:5000/v3",
            "auth": "v3applicationcredential",
            "vos": [
                {
                    "auth": {
                        "foo": "bar",
                        "password": "1234",
                        "username": "demo",
                    },
                    "name": "ops",
                },
            ],
        }
        m_get_secrets.assert_called_with(
            "https://example.com:5000/v3", "ops", "the_access_token"
        )

    def test_secretize_regular_site(self):
        r = secretize(regular_site, "the_access_token")
        assert r == regular_site

    def test_auditor_config(self):
        r = auditor_config(regular_site)
        assert r == {
            "clouds": {
                "auditor": {
                    "auth": {
                        "access_token_type": "access_token",
                        "auth_url": "https://example.com:5000/v3",
                        "client_id": None,
                        "client_secret": None,
                        "discovery_endpoint": "https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration",
                        "domain_name": "egi.eu",
                        "identity_provider": "egi.eu",
                        "openid_scope": "openid profile "
                        "eduperson_entitlement:urn:mace:egi.eu:group:cloud.egi.eu:role=auditor#aai.egi.eu "
                        "entitlements:urn:mace:egi.eu:group:cloud.egi.eu:role=auditor#aai.egi.eu "
                        "email voperson_id",
                        "protocol": "openid",
                    },
                    "auth_type": "v3oidcclientcredentials",
                },
            },
        }

    def test_full_config(self):
        print(self.conf)
        print(dir(self.conf))
        with patch("builtins.open", mock_open(read_data="{}")):
            configure("site-file")
