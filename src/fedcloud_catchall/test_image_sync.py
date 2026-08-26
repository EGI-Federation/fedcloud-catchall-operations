"""Tests for image sync"""

import configparser
from unittest.mock import MagicMock, mock_open, patch

import httpx
import respx
import testtools
import yaml
from oslo_config import fixture

from . import image_sync as sync

sample_config = """
[DEFAULT]
extractor = nova
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

disabled_sites = {1: {"id": 1, "name": "CENI", "static": {}}}


enabled_site = {
    "id": 1,
    "url": "https://example.com:5000/v3",
    "name": "CENI",
    "static": {
        "images": {"sync": True},
    },
    "shares": {"vo1": {"id": "abc", "foo": "bar", "name": "vo1"}},
}

enabled_sites = {1: enabled_site}


class TestImageSync(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    @patch("fedcloud_catchall.image_sync.run_atrope")
    def test_do_sync_disabled(self, m_run):
        sync.do_sync(disabled_sites, "foo")
        m_run.assert_not_called()

    @patch("fedcloud_catchall.image_sync.run_atrope")
    def test_do_sync_enabled(self, m_run):
        sync.do_sync(enabled_sites, "foo")
        m_run.assert_called_with(enabled_sites[1], "foo")

    @respx.mock
    def test_fetch_harbor_projects(self):
        self.conf.set_override("registry_base_url", "https://example.com", group="sync")
        self.conf.set_override("registry_user", "user", group="sync")
        self.conf.set_override("registry_password", "1234", group="sync")
        harbor_response = [
            {"name": "vo1", "foo": "bar"},
            {"name": "vo2", "baz": "foo"},
        ]
        respx.get("https://example.com/api/v2.0/projects").mock(
            return_value=httpx.Response(200, json=harbor_response)
        )
        assert sync.fetch_harbor_projects() == ["vo1", "vo2"]

    def test_dump_vo_map(self):
        assert yaml.safe_load(sync.dump_vo_map(enabled_site)) == {
            "vo1": {"foo": "bar", "id": "abc", "project_id": "abc", "name": "vo1"}
        }

    def test_dump_sources_config(self):
        projects = ["vo1", "vo2"]
        self.conf.set_override("registry_user", "user", group="sync")
        self.conf.set_override("registry_password", "1234", group="sync")
        self.conf.set_override(
            "registry_base_url", "https://registry.org", group="sync"
        )
        self.conf.set_override("registry_host", "example.com", group="sync")
        self.conf.set_override("registry_project", "project", group="sync")
        site_vo_list = ["vo1", "vo2", "vo3"]
        config = yaml.safe_load(sync.dump_sources_config(site_vo_list, projects))
        assert config == {
            "harbor": {
                "api_url": "https://registry.org/api/v2.0",
                "auth_password": "1234",
                "auth_user": "user",
                "enabled": True,
                "prefix": "registry.egi.eu ",
                "registry_host": "example.com",
                "tag_pattern": "^[^-]*$",
            },
            "project": {
                "project": "project",
                "type": "harbor",
                "vos": [
                    "vo1",
                    "vo2",
                    "vo3",
                ],
            },
            "vo1": {
                "project": "vo1",
                "type": "harbor",
                "vos": [
                    "vo1",
                ],
            },
            "vo2": {
                "project": "vo2",
                "type": "harbor",
                "vos": [
                    "vo2",
                ],
            },
        }

    def test_dump_atrope_config(self):
        parser = configparser.ConfigParser()
        parser.read_string(
            sync.dump_atrope_config(
                enabled_site, enabled_site["shares"]["vo1"]["id"], "sources", "vo_map"
            )
        )
        assert parser.sections() == [
            "glance",
            "glance_abc",
            "dispatchers",
            "cache",
            "sources",
        ]
        # check some of the values there, not getting crazy about it
        assert parser["sources"]["image_sources"] == "sources"
        assert parser["dispatchers"]["dispatcher"] == "glance"
        assert parser["glance"]["vo_map"] == "vo_map"
        assert parser["glance"]["project_id"] == "abc"
        assert parser["DEFAULT"]["state_path"] == "/atrope-state/"

    @patch("fedcloud_catchall.image_sync.dump_atrope_config")
    @patch("fedcloud_catchall.image_sync.dump_sources_config")
    @patch("fedcloud_catchall.image_sync.dump_vo_map")
    @patch("tempfile.TemporaryDirectory")
    @patch("subprocess.call")
    def test_run_atrope(self, m_subp, m_temp, m_vo, m_sources, m_atrope):
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = "/tmp"
        mock_ctx.__exit__.return_value = None
        m_temp.return_value = mock_ctx
        with patch("builtins.open", mock_open()):
            sync.run_atrope(enabled_site, ["vo1"])
        m_atrope.assert_called_with(
            enabled_site, "abc", "/tmp/sources.yaml", "/tmp/vo-map.yaml"
        )
        m_sources.assert_called_with(["vo1"], ["vo1"])
        m_vo.assert_called_with(enabled_site)
        m_subp.assert_called_with(["atrope", "--config-dir", "/tmp", "sync"])
