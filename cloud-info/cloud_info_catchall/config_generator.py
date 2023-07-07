"""Discover projects for cloud-info-povider and generate configuration

Takes its own configuration from env variables:
CHECKIN_SECRETS_FILE: yaml file with the check-in secrets to get access tokens
CHECKIN_OIDC_TOKEN: URL for token refreshal
OS_AUTH_URL, OS_IDENTITY_PROVIDER, OS_PROTOCOL: OpenStack endpoint config
SITE_NAME: site name
"""

import logging
import os

import fedcloudclient.endpoint as fedcli
import yaml
from cloud_info_provider.auth_refreshers.oidc_refresh import OidcRefreshToken


class ShareDiscovery:
    def __init__(self, auth_url, identity_provider, protocol, token_url, vo_dir):
        self.auth_url = auth_url
        self.identity_provider = identity_provider
        self.protocol = protocol
        self.token_url = token_url
        self.vo_dir = vo_dir

    def refresh_token(self, secret):
        # fake the options for refreshing
        # avoids code duplication but not very clean
        class Opt:
            timeout = 10

        refresher = OidcRefreshToken(Opt)
        return refresher._refresh_token(
            self.token_url,
            secret.get("client_id", None),
            secret.get("client_secret", None),
            secret.get("refresh_token", None),
            "openid email profile voperson_id eduperson_entitlement",
        )

    def get_token_shares(self, access_token):
        # rely on fedcloudclient for getting token
        # exchange access_token for Keystone token
        shares = {}
        try:
            token = fedcli.retrieve_unscoped_token(
                self.auth_url, access_token, self.protocol
            )
        except fedcli.TokenException:
            # this check-in account does not have access to the site, ignore
            return shares
        projects = fedcli.get_projects_from_single_site(self.auth_url, token)
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

    def generate_shares(self, secrets):
        shares = {}
        for s in secrets:
            # not our thing
            if not isinstance(secrets[s], dict):
                continue
            access_token = self.refresh_token(secrets[s])
            token_shares = self.get_token_shares(access_token)
            shares.update(token_shares)
            # create the directory structure for the cloud-info-provider
            for d in token_shares:
                dir_path = os.path.join(self.vo_dir, d)
                os.makedirs(dir_path, exist_ok=True)
                for field in "client_id", "client_secret", "refresh_token":
                    with open(os.path.join(dir_path, field), "w+") as f:
                        f.write(secrets[s].get(field, None) or "")
        if not shares:
            logging.error("No shares generated!")
            raise Exception("No shares found!")
        return shares

    def generate_config(self, site_name, secrets):
        shares = self.generate_shares(secrets)
        return {"site": {"name": site_name}, "compute": {"shares": shares}}


def read_secrets(secrets_file):
    with open(secrets_file, "r") as f:
        return yaml.load(f.read(), Loader=yaml.SafeLoader)


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
    secrets = read_secrets(checkin_secrets_file)
    disc = ShareDiscovery(
        os_auth_url, os_identity_provider, os_protocol, checkin_token_url, vo_dir
    )
    config = disc.generate_config(site_name, secrets)
    print(yaml.dump(config))


if __name__ == "__main__":
    main()
