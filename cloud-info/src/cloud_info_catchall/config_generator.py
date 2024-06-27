"""Discover projects for cloud-info-povider and generate configuration

Takes its own configuration from env variables:
SECRETS_FILE: yaml file with the secrets to access shares
The yaml includes as many credentials as wanted in 2 formats
```
---
secret_name:
    client_id:"client id"
    client_secret: "client_secret"
    refresh_token: "refresh_token"

other_secret:
    access_token: "access token"
```
Any other formats will be ignored

VO_SECRETS_PATH: directory to create VO structure with credentials
                 for cloud-info-provider
TOKEN_URL: URL to refresh tokens
OS_AUTH_URL, OS_IDENTITY_PROVIDER, OS_PROTOCOL: OpenStack endpoint config
SITE_NAME: site name
"""

import logging
import os

import yaml
from cloud_info_catchall.share_discovery import (
    AccessTokenShareDiscovery,
    RefresherShareDiscovery,
)


def read_secrets(secrets_file):
    with open(secrets_file, "r") as f:
        return yaml.load(f.read(), Loader=yaml.SafeLoader)


def generate_shares(config, secrets):
    """calls the share discovery class according to the secret type
    that we have"""
    shares = {}
    for s in secrets:
        # not our thing
        if not isinstance(secrets[s], dict):
            continue
        if "client_id" in secrets[s] and "refresh_token" in secrets[s]:
            discoverer = RefresherShareDiscovery(config, secrets[s])
        elif "access_token" in secrets[s]:
            discoverer = AccessTokenShareDiscovery(config, secrets[s])
        else:
            continue
        token_shares = discoverer.get_token_shares()
        shares.update(token_shares)
    if not shares:
        logging.error("No shares generated!")
        raise Exception("No shares found!")
    return shares


def generate_shares_config(config, secrets):
    shares = generate_shares(config, secrets)
    return {"site": {"name": config["site_name"]}, "compute": {"shares": shares}}


def main():
    logging.basicConfig()
    # get config from env
    secrets_file = os.environ["SECRETS_FILE"]
    config = {
        "auth_url": os.environ["OS_AUTH_URL"],
        "identity_provider": os.environ["OS_IDENTITY_PROVIDER"],
        "protocol": os.environ["OS_PROTOCOL"],
        "site_name": os.environ["SITE_NAME"],
        "token_url": os.environ.get("TOKEN_URL", ""),
        "vo_dir": os.environ.get("VO_SECRETS_PATH", ""),
    }
    secrets = read_secrets(secrets_file)
    shares_config = generate_shares_config(config, secrets)
    print(yaml.dump(shares_config))


if __name__ == "__main__":
    main()
