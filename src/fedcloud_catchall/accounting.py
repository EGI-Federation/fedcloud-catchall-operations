"""
Accounting operations

Creates the proper configuration files for cASO and runs it to get accounting
records for fedcloud sites
"""

import datetime
import json
import logging
import os.path
import subprocess
import sys
import tempfile

from dateutil import tz

from fedcloud_catchall.config import CONF
from fedcloud_catchall.discovery import fetch_site_info, load_sites

config_template = """
[DEFAULT]
extractor = nova, cinder, neutron
site_name = {site_name}
service_name = {service_name}
projects = {project_id}
messengers = ssm
vo_property = {vo_property}
spooldir = {spooldir}

[keystone_auth]
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

[ssm]
output_path = {ssmdir}"""


def caso_config(site, project_id, site_dir, vo_property="egi.eu:VO"):
    return config_template.format(
        site_name=site["name"],
        service_name=site["hostname"],
        auth_url=site["url"],
        client_id=CONF.checkin.client_id,
        client_secret=CONF.checkin.client_secret,
        scopes=CONF.checkin.scopes,
        discovery_endpoint=CONF.checkin.discovery_endpoint,
        project_id=project_id,
        vo_property=vo_property,
        spooldir=site_dir,
        ssmdir=os.path.join(site_dir, "outgoing"),
    )


def vo_map(site):
    vos = {}
    for project in site["projects"]:
        vos[project["name"]] = {"projects": [project["id"]]}
    return json.dumps(vos)


def run_caso(sites_config):
    sites_info = fetch_site_info()
    for site in sites_info:
        site_name = site["name"]
        # filter out those sites that are not part of the centralised ops
        if site_name not in sites_config:
            logging.debug(f"Discarding site {site_name}, not in config.")
            continue
        accounting_config = sites_config[site_name].get("accounting", {})
        if not accounting_config.get("enabled", False):
            logging.debug(f"Discarding site {site_name}, accounting not enabled.")
            continue
        site.update(accounting_config)
        site_dir = os.path.join(CONF.accounting.spool_dir, site_name)
        print(site_dir)
        os.makedirs(site_dir, exist_ok=True)
        logging.info(f"Configuring site {site_name}")
        # running caso for each project independently so we can control the "lastrun"
        for project in site["projects"]:
            with tempfile.TemporaryDirectory() as tmpdirname:
                vo_map_file = os.path.join(tmpdirname, "mapping.json")
                print(vo_map_file)
                with open(vo_map_file, "w+") as f:
                    f.write(vo_map(site))
                with open(os.path.join(tmpdirname, "caso.conf"), "w+") as f:
                    f.write(caso_config(site, project["id"], site_dir))
                cmd = [
                    "caso-extract",
                    "--config-dir",
                    tmpdirname,
                    "--mapping_file",
                    vo_map_file,
                ]
                if not os.path.exists(
                    os.path.join(site_dir, f"lastrun.{project['id']}")
                ):
                    yesterday = datetime.datetime.now(tz.tzutc()) - datetime.timedelta(
                        days=1
                    )
                    cmd.extend(["--extract-from", yesterday.isoformat()])
                    print(cmd)
                logging.debug(f"Running {' '.join(cmd)}")
                subprocess.call(cmd)


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    run_caso(load_sites())


if __name__ == "__main__":
    main()
