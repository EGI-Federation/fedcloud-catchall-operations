"""
Re-configures the site to use app credentials
"""

import logging
import os.path
import sys
from urllib.parse import urlparse

import hvac
import jwt
import yaml
from hvac.exceptions import VaultError
from oslo_config import cfg

from .config import CONF

VAULT_URL = "https://vault.services.fedcloud.eu:8200"


def secretize(site_config_file: str, access_token: str):
    site_config = {}
    with open(site_config_file, "r") as f:
        site_config = yaml.load(f, Loader=yaml.SafeLoader)
    if site_config.get("auth", None) != "v3applicationcredential":
        return site_config

    # we don't need to verify the access token here - just need the sub
    payload = jwt.decode(access_token, options={"verify_signature": False})

    client = hvac.Client(url=VAULT_URL)
    client.auth.jwt.jwt_login(role="", jwt=access_token)
    for vo in site_config.get("vos", {}):
        keystone_host = urlparse(site_config.get("endpoint", "")).netloc.split(":", 1)[
            0
        ]
        secret_path = os.path.join(
            "users",
            payload.get("sub", ""),
            "cloudmon",
            keystone_host,
            vo.get("name", ""),
        )
        try:
            appcred_args = client.secrets.kv.v1.read_secret(
                path=secret_path,
                mount_point="/secrets/",
            ).get("data", {})
            auth = vo.get("auth", {})
            auth.update(appcred_args)
        except VaultError as e:
            logging.debug(f"Ouch {e}")
    return site_config


def main():
    CONF.register_cli_opt(cfg.StrOpt("site_config", positional=True))
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    print(yaml.dump(secretize(CONF.site_config, os.environ.get("OS_ACCESS_TOKEN", ""))))


if __name__ == "__main__":
    main()
