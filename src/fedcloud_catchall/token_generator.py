"""Refreshes credentials for the cloud-info-provider"""

import calendar
import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
import jwt
from oslo_config import cfg

from .config import CONF

_oidc_config = None


def valid_token(token, oidc_config, min_time):
    if not token:
        return False
    jwks_config = httpx.get(oidc_config["jwks_uri"]).json()
    # See https://stackoverflow.com/a/68891371
    public_keys = {}
    for jwk in jwks_config["keys"]:
        kid = jwk["kid"]
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    try:
        headers = jwt.get_unverified_header(token)
        kid = headers["kid"]
        key = public_keys[kid]
        payload = jwt.decode(token, key=key, algorithms=[headers["alg"]])
        # this comes from JWT documentation
        # https://pyjwt.readthedocs.io/en/stable/usage.html#expiration-time-claim-exp
        now = calendar.timegm(datetime.now(tz=timezone.utc).utctimetuple())
        return payload["exp"] - now > min_time
    except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
        logging.warning(f"Unable to open / expired token: {e}")
        return False


def generate_token(oidc_config, scopes=None):
    if not scopes:
        scopes = CONF.checkin.scopes
    payload = {
        "grant_type": "client_credentials",
        "client_id": CONF.checkin.client_id,
        "client_secret": CONF.checkin.client_secret,
        "scope": scopes,
    }
    r = httpx.post(oidc_config["token_endpoint"], data=payload)
    return r.json()["access_token"]


def check_token(token_file, oidc_config, ttl):
    if os.path.exists(token_file):
        token = ""
        with open(token_file, "r") as f:
            token = f.read().strip()
        if valid_token(token, oidc_config, ttl):
            logging.warning(f"Token at '{token_file}' is still valid, not refreshing")
            return True
    return False


def get_oidc_config():
    global _oidc_config
    if not _oidc_config:
        _oidc_config = httpx.get(CONF.checkin.discovery_endpoint).json()
    return _oidc_config


def check_and_create_token(token_file, oidc_config, scopes=None):
    if not check_token(token_file, oidc_config, CONF.checkin.access_token_ttl):
        logging.info(f"The token at {token_file} needs refreshing")
        new_token = generate_token(oidc_config, scopes)
        with open(token_file, "w+") as f:
            f.write(new_token)


def main():
    logging.basicConfig(level=logging.DEBUG)
    CONF.register_cli_opt(cfg.StrOpt("access_token_file", positional=True))
    CONF.register_cli_opt(
        cfg.StrOpt("auditor_token_file", positional=True, required=False)
    )
    CONF(sys.argv[1:])

    oidc_config = get_oidc_config()
    check_and_create_token(CONF.access_token_file, oidc_config)
    if CONF.auditor_token_file:
        check_and_create_token(
            CONF.auditor_token_file, oidc_config, scopes=CONF.checkin.auditor_scopes
        )


if __name__ == "__main__":
    main()
