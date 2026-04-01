"""Tests for the discovery"""

from unittest.mock import MagicMock, mock_open, patch

import testtools
from oslo_config import fixture

from .cloud_info_config import secretize

app_cred_site = """
---
gocdb: TEST
endpoint: https://example.com:5000/v3
auth: v3applicationcredential
vos:
  - name: ops
    auth:
      foo: bar
"""

regular_site = """
---
gocdb: TEST
endpoint: https://example.com:5000/v3
vos:
  - name: ops
    auth:
      foo: bar
"""


class TestCloudConfig(testtools.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    @patch("jwt.decode")
    @patch("hvac.Client")
    def test_secretize_app_cred_site(self, m_hvac, m_decode):
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
        with patch("builtins.open", mock_open(read_data=app_cred_site)):
            r = secretize("site_config_file", "the_access_token")
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
        m_hvac.assert_called_once()
        m_client.auth.jwt.jwt_login.assert_called_with(role="", jwt="the_access_token")
        m_client.secrets.kv.v1.read_secret.assert_called_with(
            path="users/user@egi.eu/cloudmon/example.com/ops",
            mount_point="/secrets/",
        )

    def test_secretize_regular_site(self):
        with patch("builtins.open", mock_open(read_data=regular_site)):
            r = secretize("site_config_file", "the_access_token")
        assert r == {
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
