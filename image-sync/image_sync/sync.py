"""
Image synchronisation tool

Creates the proper configuration files for atrope and runs it to get images
synced in the EGI Fedcloud
"""

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
        cfg.StrOpt("registry_base_url", default="https://registry.egi.eu"),
        cfg.StrOpt("registry_host", default="registry.egi.eu"),
        cfg.StrOpt("registry_project", default="egi_vm_images"),
        cfg.ListOpt("formats", default=[]),
        cfg.StrOpt("registry_user"),
        cfg.StrOpt("registry_password"),
        cfg.StrOpt(
            "registry_project_map", default="/image-sync/registry-projects.yaml"
        ),
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


def fetch_harbor_projects():
    auth = httpx.BasicAuth(
        username=CONF.sync.registry_user, password=CONF.sync.registry_password
    )
    client = httpx.Client(auth=auth)

    projects = []
    page = 1
    next_url = "/api/v2.0/projects"
    params = dict(page=page, page_size=10)

    while next_url:
        url = f"{CONF.sync.registry_base_url}{next_url}"
        logging.debug(f"Fetching page {page} from {url}")
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        projects.extend(data)
        next_url = r.links.get("next", {}).get("url", None)
        print(next_url)
        params = {}
        page += 1

    # FIXME: we may want to include some metadata in harbor instead of just
    #        matching names. For now this should work
    return [p.get("name") for p in projects]


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


def dump_sources_config(site_vo_list, harbor_projects):
    harbor = {
        "harbor": {
            "enabled": True,
            "prefix": "registry.egi.eu ",
            "api_url": f"{CONF.sync.registry_base_url}/api/v2.0",
            "auth_user": CONF.sync.registry_user,
            "auth_password": CONF.sync.registry_password,
            "registry_host": CONF.sync.registry_host,
            "tag_pattern": "^[^-]*$",
        },
        # All vos uses the default registry project
        CONF.sync.registry_project: {
            "vos": site_vo_list,
            "type": "harbor",
            "project": CONF.sync.registry_project,
        },
    }
    # specific VOs use their own project
    for project in filter(lambda x: x in site_vo_list, harbor_projects):
        harbor[project] = {
            "vos": project,
            "type": "harbor",
            "project": project,
        }
    return yaml.dump(harbor)


def do_sync(sites_config, harbor_projects):
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
            site_vo_list = list(site["shares"].keys())
            ops_project_id = site["shares"]["ops"]["project_id"]
            with open(os.path.join(tmpdirname, "atrope.conf"), "w+") as f:
                f.write(
                    dump_atrope_config(site, ops_project_id, sources_file, vo_map_file)
                )
            with open(sources_file, "w+") as f:
                f.write(dump_sources_config(site_vo_list, harbor_projects))
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
    do_sync(load_sites(), fetch_harbor_projects())


if __name__ == "__main__":
    main()
