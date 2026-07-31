"""
Creates the clouds.yaml for the cloud-info-provider
Re-configures the site to use app credentials
"""

import logging
import os.path
import sys

import yaml
from oslo_config import cfg

from .config import CONF
from .discovery import get_vo_secrets


def read_site_config(site_config_file: str):
    with open(site_config_file, "r") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


def secretize(site_config: dict, access_token: str):
    if site_config.get("auth", None) != "v3applicationcredential":
        return site_config

    for vo in site_config.get("vos", {}):
        auth = vo.get("auth", {})
        auth.update(
            get_vo_secrets(
                site_config.get("endpoint", ""), vo.get("name", ""), access_token
            )
        )
    return site_config


def auditor_config(site_config: dict):
    auditor = {
        "auth": {
            "access_token_type": "access_token",
            "auth_url": site_config.get("endpoint"),
            "client_id": CONF.checkin.client_id,
            "client_secret": CONF.checkin.client_secret,
            "discovery_endpoint": CONF.checkin.discovery_endpoint,
            "domain_name": "egi.eu",
            "identity_provider": "egi.eu",
            "openid_scope": CONF.checkin.auditor_scopes,
            "protocol": site_config.get("protocol", "openid"),
        },
        "auth_type": "v3oidcclientcredentials",
    }
    return {"clouds": {"auditor": auditor}}


def configure(site_config_file: str):
    site_config = read_site_config(site_config_file)
    # config file
    print(yaml.dump(secretize(site_config, os.environ.get("OS_ACCESS_TOKEN", ""))))
    # and clouds.yaml
    with open("clouds.yaml", "w+") as f:
        f.write(yaml.dump(auditor_config(site_config)))


def main():
    CONF.register_cli_opt(cfg.StrOpt("site_config", positional=True))
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    configure(CONF.site_config)


if __name__ == "__main__":
    main()
