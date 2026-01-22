"""Tests for the discovery"""

import unittest

import httpx
import respx
import testtools
from oslo_config import fixture

import fedcloud_catchall.discovery as disco


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


if __name__ == "__main__":
    unittest.main()
