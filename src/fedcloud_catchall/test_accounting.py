"""Tests for the accounting"""

import copy
import datetime
import json
from unittest.mock import mock_open, patch

import testtools
from oslo_config import fixture

from . import accounting as acc

sample_config = """
[DEFAULT]
extractor = nova
site_name = CENI
service_name = openstack.ceni.org.cn
projects = 90c0ce1b2f1545c0b9a05d9a8fd45102
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
project_id = 90c0ce1b2f1545c0b9a05d9a8fd45102
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
    "static": {"accounting": {"enabled": True}},
}


class TestAccounting(testtools.TestCase):

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
        assert (
            acc.caso_config(
                sample_site, sample_site["projects"][0], "/var", "egi.eu:VO"
            )
            == sample_config
        )

    def test_caso_config_site_override(self):
        self.conf.set_override("scopes", "a b c", group="checkin")
        self.conf.set_override("client_id", "id", group="checkin")
        self.conf.set_override("client_secret", "secret", group="checkin")
        override_site = copy.deepcopy(sample_site)
        override_site["static"]["accounting"]["site_name"] = "FAKE"
        cfg = acc.caso_config(
            override_site, sample_site["projects"][0], "/var", "egi.eu:VO"
        )
        assert "site_name = FAKE" in (s.strip() for s in cfg.split("\n"))

    @patch("tempfile.TemporaryDirectory")
    @patch("subprocess.call")
    @patch("os.path.exists")
    @patch("fedcloud_catchall.accounting.caso_config")
    def test_site_caso_with_lastrun(self, m_caso_config, m_exists, m_subp, m_temp):
        m_temp.return_value.__enter__.return_value = "/bar"
        m_exists.return_value = True
        m_subp.return_value = 0
        with patch("builtins.open", mock_open()) as m_open:
            acc.site_caso(sample_site, "dir")
            m_open.assert_any_call("/bar/mapping.json", "w+")
            m_open.assert_any_call("/bar/caso.conf", "w+")
        caso_cmd_call = [
            "caso-extract",
            "--config-dir",
            "/bar",
            "--mapping_file",
            "/bar/mapping.json",
        ]
        m_caso_config.assert_any_call(
            sample_site, sample_site["projects"][0], "dir/block", "cinder"
        )
        m_caso_config.assert_any_call(
            sample_site, sample_site["projects"][0], "dir/compute", "nova"
        )
        m_subp.assert_called_with(caso_cmd_call)

    @patch("tempfile.TemporaryDirectory")
    @patch("subprocess.call")
    @patch("os.path.exists")
    @patch("fedcloud_catchall.accounting.caso_config")
    @patch(f"{acc.__name__}.datetime", wraps=datetime)
    def test_site_caso_no_lastrun(
        self, m_date, m_caso_config, m_exists, m_subp, m_temp
    ):
        m_temp.return_value.__enter__.return_value = "/bar"
        m_exists.return_value = False
        m_date.datetime.now.return_value = datetime.datetime(2026, 1, 1)
        with patch("builtins.open", mock_open()) as m_open:
            acc.site_caso(sample_site, "dir")
            m_open.assert_any_call("/bar/mapping.json", "w+")
            m_open.assert_any_call("/bar/caso.conf", "w+")
        caso_cmd_call = [
            "caso-extract",
            "--config-dir",
            "/bar",
            "--mapping_file",
            "/bar/mapping.json",
            "--extract-from",
            "2025-12-31T00:00:00",
        ]
        m_caso_config.assert_any_call(
            sample_site, sample_site["projects"][0], "dir/block", "cinder"
        )
        m_caso_config.assert_any_call(
            sample_site, sample_site["projects"][0], "dir/compute", "nova"
        )
        m_subp.return_value = 0
        m_subp.assert_called_with(caso_cmd_call)

    @patch("tempfile.TemporaryDirectory")
    @patch("subprocess.call")
    @patch("fedcloud_catchall.accounting.ssm_config")
    def test_site_ssm(self, m_config, m_subp, m_temp):
        m_temp.return_value.__enter__.return_value = "/bar"
        with patch("builtins.open", mock_open()) as m_open:
            acc.site_ssm(sample_site, "dir")
            m_open.assert_any_call("/bar/ssm.conf", "w+")
        m_config.assert_any_call(sample_site, "dir/compute", "eu-egi-cloud-accounting")
        m_config.assert_any_call(sample_site, "dir/block", "eu-egi-storage-accounting")
        m_subp.assert_called_with(["ssmsend", "-c", "/bar/ssm.conf"])

    @patch("fedcloud_catchall.accounting.site_caso")
    @patch("fedcloud_catchall.accounting.site_ssm")
    @patch("os.makedirs")
    def test_run_caso(self, m_mkdirs, m_ssm, m_caso):
        self.conf.set_override("spool_dir", "/foo", group="accounting")
        acc.run({1: sample_site})
        m_mkdirs.assert_called_with("/foo/CENI", exist_ok=True)
        m_ssm.assert_called_with(sample_site, "/foo/CENI")
        m_caso.assert_called_with(sample_site, "/foo/CENI")

    @patch("fedcloud_catchall.accounting.site_caso")
    @patch("fedcloud_catchall.accounting.site_ssm")
    @patch("os.makedirs")
    def test_run_site_disabled(self, m_mkdirs, m_ssm, m_caso):
        self.conf.set_override("spool_dir", "/foo", group="accounting")
        disabled_site = copy.deepcopy(sample_site)
        disabled_site["static"]["accounting"]["enabled"] = False
        acc.run({1: disabled_site})
        m_mkdirs.assert_not_called()
        m_ssm.assert_not_called()
        m_caso.assert_not_called()

    @patch("fedcloud_catchall.accounting.site_caso")
    @patch("fedcloud_catchall.accounting.site_ssm")
    @patch("os.makedirs")
    def test_run_disabled_site_forced(self, m_mkdirs, m_ssm, m_caso):
        self.conf.set_override("spool_dir", "/foo", group="accounting")
        self.conf.set_override("force_run", True, group="accounting")
        disabled_site = copy.deepcopy(sample_site)
        disabled_site["static"]["accounting"]["enabled"] = False
        acc.run({1: disabled_site})
        m_mkdirs.assert_called_with("/foo/CENI", exist_ok=True)
        m_ssm.assert_called_with(disabled_site, "/foo/CENI")
        m_caso.assert_called_with(disabled_site, "/foo/CENI")
