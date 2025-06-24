import glob
import logging
import os
import os.path
import subprocess
import sys
import tempfile

import httpx
import yaml
from oslo_config import cfg

# Configuraion
CONF = cfg.CONF
CONF.register_opts(
    [
        cfg.StrOpt("site_config_dir", default="."),
        cfg.StrOpt("cloud_info_url", default="https://is.cloud.egi.eu"),
        cfg.StrOpt("registry_api_url", default="https://registry.egi.eu/api/v2.0"),
        cfg.StrOpt("registry_host", default="registry.egi.eu"),
        cfg.StrOpt("registry_project", default="egi_vm_images"),
        cfg.ListOpt("formats", default=[]),
        cfg.StrOpt("appdb_token"),
        cfg.StrOpt("registry_user"),
        cfg.StrOpt("registry_password"),
    ],
    group="sync",
)

# Check-in config
checkin_grp = cfg.OptGroup("checkin")
CONF.register_opts(
    [
        cfg.StrOpt("client_id"),
        cfg.StrOpt("client_secret"),
        cfg.StrOpt("scopes", default="openid profile eduperson_entitlement email"),
        cfg.StrOpt(
            "discovery_endpoint",
            default="https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration",
        ),
    ],
    group="checkin",
)


def fetch_site_info_cloud_info():
    logging.debug("Fetching site info from cloud-info")
    sites = []
    # 1 - Get all sites listing
    r = httpx.get(
        os.path.join(CONF.sync.cloud_info_url, "sites/"),
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    # 2 - Go one by one getting the shares
    for site in r.json():
        try:
            r = httpx.get(
                os.path.join(CONF.sync.cloud_info_url, f"site/{site['name']}/projects")
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


def fetch_site_info():
    return fetch_site_info_cloud_info()


def dump_atrope_config(site, ops_project_id, sources_file, vo_map_file):
    config_template = """
[DEFAULT]
state_path = /atrope-state/

[glance]
auth_type = v3oidcclientcredentials
auth_url = {auth_url}
protocol = openid
identity_provider = egi.eu
client_id = {client_id}
client_secret = {client_secret}
scope = {scopes}
discovery_endpoint = {discovery_endpoint}
project_id = {project_id}
access_token_type = access_token
formats = {formats}
vo_map = {vo_map_file}
tag = atrope-catchall

[dispatchers]
dispatcher = glance

[cache]
formats = {formats}

[sources]
image_sources = {sources_file}
    """
    formats = site.get("formats", CONF.sync.formats)
    return config_template.format(
        auth_url=site["endpointURL"],
        client_id=CONF.checkin.client_id,
        client_secret=CONF.checkin.client_secret,
        scopes=CONF.checkin.scopes,
        discovery_endpoint=CONF.checkin.discovery_endpoint,
        project_id=ops_project_id,
        formats=",".join(formats),
        sources_file=sources_file,
        vo_map_file=vo_map_file,
    )


def dump_sources_config(vo_list):
    harbor = {
        CONF.sync.registry_project: {
            "enabled": True,
            "vos": vo_list,
            "type": "harbor",
            "api_url": CONF.sync.registry_api_url,
            "prefix": "registry.egi.eu ",
            "project": CONF.sync.registry_project,
            "registry_host": CONF.sync.registry_host,
            "auth_user": CONF.sync.registry_user,
            "auth_password": CONF.sync.registry_password,
            "tag_pattern": "^[^-]*$",
        }
    }
    return yaml.dump(harbor)


def do_sync(sites_config):
    sites_info = fetch_site_info()
    for site in sites_info:
        site_name = site["site"]["name"]
        # filter out those sites that are not part of the centralised ops
        if site_name not in sites_config:
            logging.debug(f"Discarding site {site_name}, not in config.")
            continue
        site_image_config = sites_config[site_name].get("images", {})
        if not site_image_config.get("sync", False):
            logging.debug(f"Discarding site {site_name}, no sync set.")
            continue
        site.update(site_image_config)
        logging.info(f"Configuring site {site_name}")
        with tempfile.TemporaryDirectory() as tmpdirname:
            sources_file = os.path.join(tmpdirname, "sources.yaml")
            vo_map_file = os.path.join(tmpdirname, "vo-map.yaml")
            vo_list = list(site["shares"].keys())
            ops_project_id = site["shares"]["ops"]["project_id"]
            with open(os.path.join(tmpdirname, "atrope.conf"), "w+") as f:
                f.write(
                    dump_atrope_config(site, ops_project_id, sources_file, vo_map_file)
                )
            with open(sources_file, "w+") as f:
                f.write(dump_sources_config(vo_list))
            with open(vo_map_file, "w+") as f:
                f.write(yaml.dump(site["shares"]))
            cmd = [
                "atrope",
                "--config-dir",
                tmpdirname,
                "sync",
            ]
            logging.debug(f"Running {' '.join(cmd)}")
            subprocess.call(cmd)


def load_sites():
    sites = {}
    for site_file in glob.iglob("*.yaml", root_dir=CONF.sync.site_config_dir):
        with open(os.path.join(CONF.sync.site_config_dir, site_file), "r") as f:
            site = yaml.safe_load(f.read())
            sites[site["gocdb"]] = site
    return sites


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    do_sync(load_sites())


if __name__ == "__main__":
    main()
