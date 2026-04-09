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

from .config import CONF
from .discovery import auth_config, load_sites

caso_config_template = """
[DEFAULT]
extractor = {extractor}
site_name = {site_name}
service_name = {service_name}
projects = {project_id}
messengers = ssm
vo_property = {vo_property}
spooldir = {spooldir}

{auth_section}

[ssm]
output_path = {ssmdir}"""

ssm_config_template = """
[sender]
protocol: AMS

[broker]
# msg.argo.grnet.gr is for production data
host: msg.argo.grnet.gr

[certificates]
certificate: /etc/grid-security/hostcert.pem
key: /etc/grid-security/hostkey.pem
capath: /etc/grid-security/certificates

[messaging]
# If using AMS this is the project that SSM will connect to. Ignored for STOMP.
ams_project: accounting
destination: eu-egi-cloud-accounting

# Outgoing messages will be read and removed from this directory.
path: {ssmdir}
path_type: dirq

[logging]
logfile: /var/log/apel/ssmsend.log
# Available logging levels:
# DEBUG, INFO, WARN, ERROR, CRITICAL
level: INFO
console: true
"""


def caso_config(site, vo, site_dir, vo_property="egi.eu:VO", extractor="nova"):
    site_name = site["static"].get("accounting").get("site_name", site["name"])
    auth_section = auth_config(site, vo, "keystone_auth")
    return caso_config_template.format(
        site_name=site_name,
        auth_section=auth_section,
        service_name=site["hostname"],
        project_id=vo["id"],
        vo_property=vo_property,
        spooldir=site_dir,
        extractor=extractor,
        ssmdir=os.path.join(site_dir, "outgoing"),
    )


def ssm_config(site, site_dir):
    return ssm_config_template.format(
        ssmdir=os.path.join(site_dir, "outgoing"),
    )


def vo_map(site):
    vos = {}
    for project in site["projects"]:
        vos[project["name"]] = {"projects": [project["id"]]}
    return json.dumps(vos)


def site_caso(site, site_dir):
    # running caso for each project independently so we can control the "lastrun"
    good_run = False
    for project in site["projects"]:
        with tempfile.TemporaryDirectory() as tmpdirname:
            vo_map_file = os.path.join(tmpdirname, "mapping.json")
            with open(vo_map_file, "w+") as f:
                f.write(vo_map(site))
            with open(os.path.join(tmpdirname, "caso.conf"), "w+") as f:
                f.write(caso_config(site, project, site_dir))
            cmd = [
                "caso-extract",
                "--config-dir",
                tmpdirname,
                "--mapping_file",
                vo_map_file,
            ]
            if not os.path.exists(os.path.join(site_dir, f"lastrun.{project['id']}")):
                yesterday = datetime.datetime.now(tz.tzutc()) - datetime.timedelta(
                    days=1
                )
                cmd.extend(["--extract-from", yesterday.isoformat()])
            logging.debug(f"Running {' '.join(cmd)}")
            return_code = subprocess.call(cmd)
            logging.debug(f"Return code {return_code}")
            good_run = True
    return good_run


def site_ssm(site, site_dir):
    with tempfile.TemporaryDirectory() as tmpdirname:
        ssm_config_file = os.path.join(tmpdirname, "ssm.conf")
        with open(ssm_config_file, "w+") as f:
            f.write(ssm_config(site, site_dir))
        cmd = [
            "ssmsend",
            "-c",
            ssm_config_file,
        ]
        logging.debug(f"Running {' '.join(cmd)}")
        return_code = subprocess.call(cmd)
        return return_code == 0
    return False


def run(sites):
    for _, site in sites.items():
        site_name = site["name"]
        logging.info(f"Configuring site {site_name}")
        accounting_config = site["static"].get("accounting", {})
        if not accounting_config.get("enabled", False):
            if CONF.accounting.force_run:
                logging.info(f"Force run the extraction of records for {site_name}.")
            else:
                logging.debug(f"Discarding site {site_name}, accounting not enabled.")
                continue
        site_dir = os.path.join(CONF.accounting.spool_dir, site["name"])
        os.makedirs(site_dir, exist_ok=True)
        if site_caso(site, site_dir):
            site_ssm(site, site_dir)


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    run(load_sites())


if __name__ == "__main__":
    main()
