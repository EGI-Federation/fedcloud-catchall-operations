"""
Re-configures the site to use app credentials
"""

import logging
import os.path
import sys

import yaml
from oslo_config import cfg

from .config import CONF
from .discovery import get_vo_secrets


def secretize(site_config_file: str, access_token: str):
    site_config = {}
    with open(site_config_file, "r") as f:
        site_config = yaml.load(f, Loader=yaml.SafeLoader)
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


def main():
    CONF.register_cli_opt(cfg.StrOpt("site_config", positional=True))
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    print(yaml.dump(secretize(CONF.site_config, os.environ.get("OS_ACCESS_TOKEN", ""))))


if __name__ == "__main__":
    main()
