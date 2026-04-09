"""Tests for the discovery"""

from unittest.mock import mock_open, patch

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

    @patch("fedcloud_catchall.cloud_info_config.get_vo_secrets")
    def test_secretize_app_cred_site(self, m_get_secrets):
        m_get_secrets.return_value = {
            "username": "demo",
            "password": "1234",
        }
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
        m_get_secrets.assert_called_with(
            "https://example.com:5000/v3", "ops", "the_access_token"
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
