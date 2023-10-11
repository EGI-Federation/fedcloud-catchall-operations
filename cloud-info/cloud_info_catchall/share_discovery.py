"""Discover projects for cloud-info-povider and generate configuration
"""

import logging
import os

import fedcloudclient.endpoint as fedcli
import yaml
from cloud_info_provider.auth_refreshers.oidc_refresh import OidcRefreshToken


class ShareDiscovery:
    def __init__(self, config, secret):
        self.auth_url = config["auth_url"]
        self.identity_provider = config["identity_provider"]
        self.protocol = config["protocol"]
        self.secret = secret

    def build_share(self, project, access_token):
        return {"auth": {"project_id": project["id"]}}

    def get_token_shares(self):
        access_token = self.get_token()
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
            shares[vo] = self.build_share(p, access_token)
        self.config_shares(shares, access_token)
        return shares

    def config_shares(self, shares, access_token):
        """do any additional configuration to support the shares"""
        pass

    def generate_shares(self, secrets):
        shares = {}
        for s in secrets:
            # not our thing
            if not isinstance(secrets[s], dict):
                continue
            access_token = self.get_token(secrets[s])
            token_shares = self.get_token_shares(access_token)
            shares.update(token_shares)
        if not shares:
            logging.error("No shares generated!")
            raise Exception("No shares found!")
        return shares

    def get_token(self):
        raise NotImplemented


class RefresherShareDiscovery(ShareDiscovery):
    """Refreshes tokens using a refresh token and creates a VO configuration
    for its refresh again by cloud-info-provider"""

    def __init__(self, config, secret):
        super().__init__(config, secret)
        self.token_url = config["token_url"]

    def get_token(self):
        # fake the options for refreshing
        # avoids code duplication but not very clean
        class Opt:
            timeout = 10

        refresher = OidcRefreshToken(Opt)
        return refresher._refresh_token(
            self.token_url,
            self.secret.get("client_id", None),
            self.secret.get("client_secret", None),
            self.secret.get("refresh_token", None),
            "openid email profile voperson_id eduperson_entitlement",
        )

    def config_shares(self, shares, access_token):
        # create the directory structure for the cloud-info-provider
        for d in shares:
            dir_path = os.path.join(self.vo_dir, d)
            os.makedirs(dir_path, exist_ok=True)
            for field in "client_id", "client_secret", "refresh_token":
                with open(os.path.join(dir_path, field), "w+") as f:
                    f.write(self.secret.get(field, None) or "")


class AccessTokenShareDiscovery(ShareDiscovery):
    """Uses existing access token to create VO configuration"""

    def get_token(self):
        return secret["access_token"]

    def build_share(self, project, access_token):
        s = super().build_share(project, access_token)
        s["auth"].update({"access_token": access_token})
        return s
