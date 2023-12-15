import logging
import os
import os.path
import subprocess
import sys
import tempfile

import requests
import yaml
from oslo_config import cfg

# Configuraion
CONF = cfg.CONF
CONF.register_opts(
    [
        cfg.StrOpt("sites_file", default="sites.yaml"),
        cfg.StrOpt("graphql_url", default="https://is.appdb.egi.eu/graphql"),
        cfg.ListOpt("formats", default=[]),
        cfg.StrOpt("appdb_token"),
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


def fetch_site_info():
    logging.debug("Fetching site info from AppDB")
    query = """
        {
            siteCloudComputingEndpoints{
              items{
                endpointURL
                site {
                  name
                }
                shares: shareList {
                  VO
                  entityCreationTime
                  projectID
                }
              }
            }
        }
    """
    params = {"query": query}
    r = requests.get(
        CONF.sync.graphql_url, params=params, headers={"accept": "application/json"}
    )
    r.raise_for_status()
    data = r.json()["data"]["siteCloudComputingEndpoints"]["items"]
    return data


def dump_atrope_config(site, share, hepix_file):
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

[dispatchers]
dispatcher = glance

[cache]
formats = {formats}

[sources]
hepix_sources = {hepix_file}
    """
    formats = site.get("formats", CONF.sync.formats)
    return config_template.format(
        auth_url=site["endpointURL"],
        client_id=CONF.checkin.client_id,
        client_secret=CONF.checkin.client_secret,
        scopes=CONF.checkin.scopes,
        discovery_endpoint=CONF.checkin.discovery_endpoint,
        project_id=share["projectID"],
        formats=",".join(formats),
        hepix_file=hepix_file,
    )


def dump_hepix_config(share):
    hepix = {
        share["VO"]: {
            "enabled": True,
            "endorser": {
                "ca": "/DC=ORG/DC=SEE-GRID/CN=SEE-GRID CA 2013",
                "dn": "/DC=EU/DC=EGI/C=NL/O=Hosts/O=EGI.eu/CN=appdb.egi.eu",
            },
            "prefix": "EGI ",
            "project": share["projectID"],
            "token": CONF.sync.appdb_token,
            "url": f"https://vmcaster.appdb.egi.eu/store/vo/{share['VO']}/image.list",
        }
    }
    return yaml.dump(hepix)


def do_sync(sites_config):
    sites_info = fetch_site_info()
    for site in sites_info:
        site_name = site["site"]["name"]
        # filter out those sites that are not part of the centralised ops
        if site_name not in sites_config:
            logging.debug(f"Discarding site {site_name}.")
            continue
        site.update(sites_config[site_name])
        logging.info(f"Configuring site {site_name}")
        for share in site["shares"]:
            logging.info(f"Configuring {share['VO']}")
            with tempfile.TemporaryDirectory() as tmpdirname:
                hepix_file = os.path.join(tmpdirname, "hepix.yaml")
                with open(os.path.join(tmpdirname, "atrope.conf"), "w+") as f:
                    f.write(dump_atrope_config(site, share, hepix_file))
                with open(hepix_file, "w+") as f:
                    f.write(dump_hepix_config(share))
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
    if os.path.exists(CONF.sync.sites_file):
        with open(CONF.sync.sites_file, "r") as f:
            sites = yaml.safe_load(f.read())
    return sites


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    do_sync(load_sites())


if __name__ == "__main__":
    main()
