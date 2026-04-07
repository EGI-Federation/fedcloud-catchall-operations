"""
Configuration discovery for the different sites
"""

import glob
import logging
import os.path
from urllib.parse import urlparse

import httpx
import hvac
import jwt
import yaml
from hvac.exceptions import VaultError

from .config import CONF

_hvac_client = None
VAULT_URL = "https://vault.services.fedcloud.eu:8200"


def fetch_site_info():
    logging.debug("Fetching site info from cloud-info")
    # 1 - Get all sites listing
    r = httpx.get(
        os.path.join(CONF.discovery.fedcloud_info_system_url, "sites/"),
        params={"include_projects": True},
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    sites = r.json()
    # 2 - Go one by one getting the shares
    for site in sites:
        # turn this into a more friendly structure for the rest of the code
        site["shares"] = {p["name"]: p for p in site["projects"]}
    return sites


def get_vo_secrets(endpoint: str, vo_name: str, access_token: str):
    payload = jwt.decode(access_token, options={"verify_signature": False})

    global _hvac_client
    if not _hvac_client:
        _hvac_client = hvac.Client(url=VAULT_URL)
        _hvac_client.auth.jwt.jwt_login(role="", jwt=access_token)
    keystone_host = urlparse(endpoint).netloc.split(":", 1)[0]
    secret_path = os.path.join(
        "users", payload.get("sub", ""), "cloudmon", keystone_host, vo_name
    )
    try:
        return _hvac_client.secrets.kv.v1.read_secret(
            path=secret_path,
            mount_point="/secrets/",
        ).get("data", {})
    except VaultError as e:
        logging.debug(f"Ouch {e}")
        return {}


def load_sites():
    sites = {}
    api_sites = fetch_site_info()
    static_sites = {}
    for site_file in glob.iglob("*.yaml", root_dir=CONF.discovery.site_config_dir):
        with open(os.path.join(CONF.discovery.site_config_dir, site_file), "r") as f:
            site = yaml.safe_load(f.read())
            static_sites[site["gocdb"]] = site
    for site in api_sites:
        site_name = site["name"]
        static_site = static_sites.get(site_name, None)
        if not static_sites:
            logging.debug(f"Discarding site {site_name}, not in config.")
            continue
        for vo in static_site["vos"]:
            if vo["name"] in site["shares"]:
                site["shares"][vo["name"]]["auth"] = vo["auth"]
        site["static"] = static_site
        sites[site["id"]] =  site
    return sites
