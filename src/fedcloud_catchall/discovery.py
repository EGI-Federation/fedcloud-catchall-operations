"""
Configuration discovery for the different sites
"""

import glob
import logging
import os.path

import httpx
import yaml

from fedcloud_catchall.config import CONF


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


def load_sites():
    sites = {}
    for site_file in glob.iglob("*.yaml", root_dir=CONF.discovery.site_config_dir):
        with open(os.path.join(CONF.discovery.site_config_dir, site_file), "r") as f:
            site = yaml.safe_load(f.read())
            sites[site["gocdb"]] = site
    return sites
