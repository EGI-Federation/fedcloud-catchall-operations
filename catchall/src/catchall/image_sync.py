"""
Image synchronisation tool

Creates the proper configuration files for atrope and runs it to get images
synced in the EGI Fedcloud
"""

import logging
import os.path
import subprocess
import sys
import tempfile

import httpx
import yaml

from catchall.config import CONF
from catchall.discovery import fetch_site_info, load_sites


# Harbor interaction
def fetch_harbor_projects():
    if not (CONF.sync.registry_user and CONF.sync.registry_password):
        raise ValueError("Missing credentials for registry")

    auth = httpx.BasicAuth(
        username=CONF.sync.registry_user, password=CONF.sync.registry_password
    )
    client = httpx.Client(auth=auth)

    projects = []
    page = 1
    next_url = "/api/v2.0/projects"
    params = dict(page=page, page_size=10)

    last_url = ""
    while next_url:
        if last_url == next_url:
            break
        url = f"{CONF.sync.registry_base_url}{next_url}"
        logging.debug(f"Fetching page {page} from {url}")
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        projects.extend(data)
        last_url = next_url
        next_url = r.links.get("next", {}).get("url", None)
        params = {}
        page += 1

    # FIXME: we may want to include some metadata in harbor instead of just
    #        matching names. For now this should work
    project_names = [p.get("name") for p in projects]
    logging.debug(f'Obtained {", ".join(project_names)} from Harbor')
    return project_names


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
            "vos": [project],
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


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    do_sync(load_sites(), fetch_harbor_projects())


if __name__ == "__main__":
    main()
