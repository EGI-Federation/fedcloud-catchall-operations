"""Refreshes credentials for the cloud-info-provider

Takes its own configuration from env variables:
CHECKIN_SECRETS_FILE: yaml file with the check-in secrets to get access tokens
CHECKIN_SCOPES: Scopes to request in the access token
CHECKIN_OIDC_URL: Discovery URL for Check-in
ACCESS_TOKEN_SECRETS_FILE: File where to dump the new access tokens if needed
ACCESS_TOKEN_TTL: Minimum TTL for the access token
"""

import calendar
import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
import jwt
from catchall.config import CONF
from oslo_config import cfg


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


def generate_token(oidc_config):
    payload = {
        "grant_type": "client_credentials",
        "client_id": CONF.checkin.client_id,
        "client_secret": CONF.checkin.client_secret,
        "scope": CONF.checkin.scopes,
    }
    r = httpx.post(oidc_config["token_endpoint"], data=payload)
    return r.json()["access_token"]


def check_token(token_file, oidc_config, ttl):
    if os.path.exists(token_file):
        token = ""
        with open(token_file, "r") as f:
            token = f.read().strip()
        if valid_token(token, oidc_config, ttl):
            logging.warning("Token is still valid, not refreshing")
            return True
    return False


def main():
    logging.basicConfig()
    CONF.register_cli_opt(cfg.StrOpt("access_token_file", positional=True))
    CONF(sys.argv[1:])

    oidc_config = httpx.get(CONF.checkin.discovery_endpoint).json()

    if not check_token(
        CONF.access_token_file, oidc_config, CONF.checkin.access_token_ttl
    ):
        logging.info("Token needs refreshing")
        with open(CONF.access_token_file, "w+") as f:
            new_token = generate_token(oidc_config)
            f.write(new_token)


if __name__ == "__main__":
    main()
