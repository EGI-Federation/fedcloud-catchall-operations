#!/usr/bin/env python

import argparse
import json

import yaml

CHECKIN_ISS = "https://aai.egi.eu/oidc/"


def basic_mapping(local_group, entitlement):
    return {
        "local": [{"user": {"name": "{0}"}, "group": {"id": local_group}}],
        "remote": [
            {"type": "HTTP_OIDC_SUB"},
            {"type": "HTTP_OIDC_ISS", "any_one_of": [CHECKIN_ISS]},
            {
                "type": "OIDC-eduperson_entitlement",
                "regex": True,
                "any_one_of": [f"^{entitlement}$"],
            },
        ],
    }


def get_entitlements(fqan, entitlements):
    try:
        return entitlements[fqan]
    except Keyerror:
        if not fqan.startswith("/"):
            raise Exception(f"No entitlement defined for vo {fqan}")
        # FQAN is /<name of the VO>/extra/
        #      or /VO=<name of the VO>/extra/
        vo_name = fqan.split[1]
        if vo_name.startswith("VO="):
            vo_name = vo_name[3:]
        try:
            return entitlements[vo_name]
        except Keyerror:
            raise Exception(f"No entitlement defined for vo {vo_name}")


def keystone_config(site, entitlements):
    mapping = []
    for vo in site.get("vos", []):
        ent = get_entitlements(vo["name"], entitlements)
        vo_project = vo["auth"]["project_id"]
        mapping.append(basic_mapping(vo_project, ent))
    print(json.dumps(mapping, indent=4))


def caso_config(site, *args):
    mapping = {}
    for vo in site.get("vos", []):
        vo_name = get_vo_name_from_fqan(vo["name"])
        vo_project = vo["auth"]["project_id"]
        mapping[vo_name] = {"projects": [vo_project]}
    print(json.dumps(mapping, indent=4))


def cloudkeeper_config(site, *args):
    mapping = {}
    for vo in site.get("vos", []):
        vo_name = vo["name"]
        vo_project = vo["auth"]["project_id"]
        mapping[vo_name] = {"tenant": vo_project}
    print(json.dumps(mapping, indent=4))


def load_config(f):
    return yaml.safe_load(open(f))


def main():
    parser = argparse.ArgumentParser(
        description="Generate config files for EGI integration."
    )
    parser.add_argument("site", metavar="SITE.yaml", help="site config file", nargs=1)
    parser.add_argument(
        "--vo-mappings",
        default="vo-mappings.yaml",
        help="File with the default mappings",
    )
    parser.add_argument(
        "--config-type",
        default="keystone",
        choices=["keystone", "caso", "cloudkeeper-os"],
        help="Type of configuration to generate",
    )
    args = parser.parse_args()
    site = load_config(args.site[0])
    entitlements = load_config(args.vo_mappings)["vos"]
    config_options = {
        "keystone": keystone_config,
        "caso": caso_config,
        "cloudkeeper-os": cloudkeeper_config,
    }
    config_options[args.config_type](site, entitlements)


if __name__ == "__main__":
    main()
