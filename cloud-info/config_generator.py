#!/usr/bin/env python3
"""Discover projects for cloud-info-povider and generate configuration

Takes its own configuration from env variables:
CHECKIN_SECRETS_FILE: yaml file with the check-in secrets to get access tokens
CHECKIN_OIDC_TOKEN: URL for token refreshal
OS_AUTH_URL, OS_IDENTITY_PROVIDER, OS_PROTOCOL: OpenStack endpoint config
SITE_NAME: site name
"""

import logging
import os

import yaml
from cloud_info_provider.auth_refreshers.oidc_refresh import OidcRefreshToken
from fedcloudclient.endpoint import (
    get_projects_from_single_site,
    retrieve_unscoped_token,
)


def refresh_token(token_url, secrets):
    # fake the options for refreshing
    # avoids code duplication but not very clean
    class Opt:
        timeout = 10

    refresher = OidcRefreshToken(Opt)
    return refresher._refresh_token(
        token_url,
        secrets.get("client_id", None),
        secrets.get("client_secret", None),
        secrets.get("refresh_token", None),
        "openid email profile voperson_id eduperson_entitlement",
    )


def get_shares(auth_url, identity_provider, protocol, access_token):
    # rely on fedcloudclient for getting token
    # exchange access_token for Keystone token
    token = retrieve_unscoped_token(auth_url, access_token, protocol)
    projects = get_projects_from_single_site(auth_url, token)
    shares = {}
    for p in projects:
        vo = p.get("VO", None)
        if not vo:
            logging.warning(
                "Discarding project %s as it does not have VO property", p["name"]
            )
            continue
        if not p.get("enabled", False):
            logging.warning("Discarding project %s as it is not enabled", p["name"])
            continue
        shares[vo] = {"auth": {"project_id": p["id"]}}
    return shares


def main():
    logging.basicConfig()
    # get config from env
    checkin_secrets_file = os.environ["CHECKIN_SECRETS_FILE"]
    checkin_token_url = os.environ["CHECKIN_OIDC_TOKEN"]
    os_auth_url = os.environ["OS_AUTH_URL"]
    os_identity_provider = os.environ["OS_IDENTITY_PROVIDER"]
    os_protocol = os.environ["OS_PROTOCOL"]
    site_name = os.environ["SITE_NAME"]
    vo_dir = os.environ["VO_SECRETS_PATH"]
    with open(checkin_secrets_file, "r") as f:
        secrets = yaml.load(f.read(), Loader=yaml.SafeLoader)
    shares = {}
    for s in secrets:
        # not our thing
        if not isinstance(secrets[s], dict):
            continue
        access_token = refresh_token(checkin_token_url, secrets[s])
        secret_shares = get_shares(
            os_auth_url, os_identity_provider, os_protocol, access_token
        )
        shares.update(secret_shares)
        # create the directory structure for the cloud-info-provider
        for d in secret_shares:
            dir_path = os.path.join(vo_dir, d)
            os.makedirs(dir_path, exist_ok=True)
            for field in "client_id", "client_secret", "refresh_token":
                with open(os.path.join(dir_path, field), "w+") as f:
                    f.write(secrets[s].get(field, None) or "")
    config = {"site": {"name": site_name}, "compute": {"shares": shares}}
    print(yaml.dump(config))


if __name__ == "__main__":
    main()
