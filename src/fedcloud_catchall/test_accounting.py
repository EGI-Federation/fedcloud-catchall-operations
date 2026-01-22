"""Tests for the accounting"""

import datetime
import json
from unittest.mock import mock_open, patch

import testtools
from oslo_config import fixture

import fedcloud_catchall.accounting as acc

sample_config = """
[DEFAULT]
extractor = nova, cinder, neutron
site_name = CENI
service_name = openstack.ceni.org.cn
projects = foo
messengers = ssm
vo_property = egi.eu:VO
spooldir = /var

[keystone_auth]
auth_type = v3oidcclientcredentials
auth_url = https://openstack.ceni.org.cn:5000/v3
protocol = openid
identity_provider = egi.eu
client_id = id
client_secret = secret
scope = a b c
discovery_endpoint = https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration
project_id = foo
access_token_type = access_token

[ssm]
output_path = /var/outgoing"""

sample_site = {
    "id": "15810G0",
    "name": "CENI",
    "url": "https://openstack.ceni.org.cn:5000/v3",
    "state": "",
    "hostname": "openstack.ceni.org.cn",
    "projects": [
        {"id": "90c0ce1b2f1545c0b9a05d9a8fd45102", "name": "ops"},
        {"id": "b106744c783543518f505dda45632697", "name": "vo.access.egi.eu"},
    ],
}


class TestDiscovery(testtools.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    def test_vo_map(self):
        m = json.loads(acc.vo_map(sample_site))
        assert m == {
            "ops": {"projects": ["90c0ce1b2f1545c0b9a05d9a8fd45102"]},
            "vo.access.egi.eu": {"projects": ["b106744c783543518f505dda45632697"]},
        }

    def test_caso_config(self):
        self.conf.set_override("scopes", "a b c", group="checkin")
        self.conf.set_override("client_id", "id", group="checkin")
        self.conf.set_override("client_secret", "secret", group="checkin")
        assert acc.caso_config(sample_site, "foo", "/var", "egi.eu:VO") == sample_config

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("os.makedirs")
    def test_run_caso_no_sites(self, m_mkdirs, m_fetch):
        m_fetch.return_value = [sample_site]
        acc.run_caso({})
        m_mkdirs.assert_not_called()

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("os.makedirs")
    def test_run_caso_no_sites_enables(self, m_mkdirs, m_fetch):
        m_fetch.return_value = [sample_site]
        acc.run_caso({"CENI": {"accounting": {"enabled": False}}})
        m_mkdirs.assert_not_called()

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("os.makedirs")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.path.exists")
    @patch("subprocess.call")
    def test_run_caso_one_site(self, m_subp, m_exists, m_temp, m_mkdirs, m_fetch):
        self.conf.set_override("spool_dir", "/foo", group="accounting")
        m_fetch.return_value = [sample_site]
        m_temp.return_value.__enter__.return_value = "/bar"
        m_exists.return_value = True
        with patch("builtins.open", mock_open()) as m_open:
            acc.run_caso({"CENI": {"accounting": {"enabled": True}}})
            m_open.assert_any_call("/bar/mapping.json", "w+")
            m_open.assert_any_call("/bar/caso.conf", "w+")
        m_mkdirs.assert_called_once_with("/foo/CENI", exist_ok=True)
        m_subp.assert_called_once_with(
            [
                "caso-extract",
                "--config-dir",
                "/bar",
                "--mapping_file",
                "/bar/mapping.json",
            ]
        )

    @patch("fedcloud_catchall.discovery.fetch_site_info")
    @patch("os.makedirs")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.path.exists")
    @patch("subprocess.call")
    @patch(f"{acc.__name__}.datetime", wraps=datetime)
    def test_run_caso_one_site(
        self, m_date, m_subp, m_exists, m_temp, m_mkdirs, m_fetch
    ):
        self.conf.set_override("spool_dir", "/foo", group="accounting")
        m_fetch.return_value = [sample_site]
        m_temp.return_value.__enter__.return_value = "/bar"
        m_exists.return_value = False
        m_date.datetime.now.return_value = datetime.datetime(2026, 1, 1)
        # other calls to datetime functions will be forwarded to original datetime
        with patch("builtins.open", mock_open()) as m_open:
            m_date.return_value = "aaa"
            acc.run_caso({"CENI": {"accounting": {"enabled": True}}})
            m_open.assert_any_call("/bar/mapping.json", "w+")
            m_open.assert_any_call("/bar/caso.conf", "w+")
        m_mkdirs.assert_called_once_with("/foo/CENI", exist_ok=True)
        m_subp.assert_called_once_with(
            [
                "caso-extract",
                "--config-dir",
                "/bar",
                "--mapping_file",
                "/bar/mapping.json",
                "--extract-from",
                "2025-12-31T00:00:00",
            ]
        )
