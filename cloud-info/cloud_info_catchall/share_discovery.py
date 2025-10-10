"""Discover projects for cloud-info-povider and generate configuration"""

import logging
import os

import requests
from keystoneauth1 import session
from keystoneauth1.exceptions.base import ClientException
from keystoneauth1.identity.v3.oidc import OidcAccessToken
from keystoneclient.v3 import client
from keystoneclient.v3.auth import AuthManager


class ShareDiscovery:
    def __init__(self, config, secret):
        self.auth_url = config["auth_url"]
        self.identity_provider = config["identity_provider"]
        self.protocol = config["protocol"]
        self.secret = secret
        self.vo_fallback = config.get("vo_fallback", {})

    def build_share(self, project, access_token):
        return {"auth": {"project_id": project["id"]}}

    def get_project_vos(self, project):
        if not project.get("enabled", False):
            logging.warning(
                f"Discarding project {project['name']} as it is not enabled"
            )
            return []
        vo = project.get("egi.VO", None)
        if not vo:
            vo = project.get("VO", None)
            if not vo:
                logging.warning(f"Project {project['name']} does not have VO property")
                vo = self.vo_fallback.get(project.get("id", None), None)
                if not vo:
                    logging.warning(
                        f"Discarding project {project['name']} as it's not known"
                    )
                    return []
        return vo.split(",")

    def get_token_shares(self):
        access_token = self.get_token()
        # exchange access_token for Keystone token
        shares = {}
        try:
            sess = session.Session(
                auth=OidcAccessToken(
                    auth_url=self.auth_url,
                    identity_provider="egi.eu",
                    protocol=self.protocol,
                    access_token=access_token,
                )
            )
            ks = client.Client(session=sess, endpoint_override=self.auth_url)
            ks.include_metadata = False
            for p in AuthManager(ks).projects():
                proj_dict = p.to_dict()
                for vo in self.get_project_vos(proj_dict):
                    shares[vo.strip()] = self.build_share(proj_dict, access_token)
            self.config_shares(shares, access_token)
        except ClientException:
            # this check-in account does not have access to the site, ignore
            pass
        return shares

    def config_shares(self, shares, access_token):
        """do any additional configuration to support the shares"""
        pass

    def get_token(self):
        raise NotImplementedError


class RefresherShareDiscovery(ShareDiscovery):
    """Refreshes tokens using a refresh token and creates a VO configuration
    for its refresh again by cloud-info-provider"""

    def __init__(self, config, secret):
        super().__init__(config, secret)
        self.token_url = config["token_url"]
        self.vo_dir = config["vo_dir"]

    def get_token(self):
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.secret.get("refresh_token", None),
            "scope": "openid email profile voperson_id eduperson_entitlement entitlements",
        }
        auth = None
        if self.secret.get("client_secret", None):
            refresh_data["client_secret"] = self.secret.get("client_secret")
            auth = (self.secret["client_id"], self.secret["client_secret"])
        r = requests.post(
            self.token_url,
            auth=auth,
            data=refresh_data,
            timeout=10,
        )
        if r.status_code != requests.codes["ok"]:
            msg = "Unable to get token, request returned %s" % r.text
            raise Exception(msg)
        return r.json()["access_token"]

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
        return self.secret["access_token"]
