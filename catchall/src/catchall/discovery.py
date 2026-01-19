"""
Configuration discovery for the different sites
"""

import glob
import logging
import os.path

import httpx
import yaml
from catchall.config import CONF


def fetch_site_info():
    logging.debug("Fetching site info from cloud-info")
    sites = []
    # 1 - Get all sites listing
    r = httpx.get(
        os.path.join(CONF.discovery.fedcloud_info_system_url, "sites/"),
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    # 2 - Go one by one getting the shares
    for site in r.json():
        try:
            r = httpx.get(
                os.path.join(
                    CONF.discovery.cloud_info_url, f"site/{site['name']}/projects"
                )
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            logging.warning(
                f"Exception while trying to get info from {site['name']}: {e}"
            )
            continue
        shares = {proj["name"]: {"project_id": proj["id"]} for proj in r.json()}
        sites.append(
            {
                "site": {"name": site["name"]},
                "endpointURL": site["url"],
                "shares": shares,
            }
        )
    return sites


def load_sites():
    sites = {}
    for site_file in glob.iglob("*.yaml", root_dir=CONF.discovery.site_config_dir):
        with open(os.path.join(CONF.discovery.site_config_dir, site_file), "r") as f:
            site = yaml.safe_load(f.read())
            sites[site["gocdb"]] = site
    return sites
