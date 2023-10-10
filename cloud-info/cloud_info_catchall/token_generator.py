"""Refreshes credentials for the cloud-info-provider

Takes its own configuration from env variables:
CHECKIN_SECRETS_FILE: yaml file with the check-in secrets to get access tokens
CHECKIN_OIDC_TOKEN: URL for token refreshal
CHECKIN_SCOPES: Scopes to request in the access token
ACCESS_TOKEN_DIR: Directory with the current access tokens / where to dump the new ones
ACCESS_TOKEN_TTL: Minimum TTL for the access token
"""

import calendar
from datetime import datetime, timezone
import json
import logging
import os

import requests
import yaml
import jwt

# Default OIDC URL for Check-in
CHECKIN_OIDC_URL = "https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration"
# Default list of scopes
CHECKIN_SCOPES = "openid profile eduperson_entitlement email"
# Default access token TTL: 20 minutes
ACCESS_TOKEN_TTL = 20 * 60


def read_secrets(secrets_file):
    with open(secrets_file, "r") as f:
        return yaml.load(f.read(), Loader=yaml.SafeLoader)


def get_access_token(token_url, scopes, secret):
    payload = {
        "grant_type": "client_credentials",
        "client_id": secret["client_id"],
        "client_secret": secret["client_secret"],
        "scope": scopes,
    }
    r = requests.post(token_url, data=payload)
    return r.json()["access_token"]


def valid_token(token_file, oidc_config, min_time):
    try:
        with open(token_file, "r") as f:
            access_token = f.read()
    except FileNotFoundError as e:
        logging.info(f"Previous access token not found: {e}")
        return False
    jwks_config = requests.get(oidc_config["jwks_uri"]).json()
    # See https://stackoverflow.com/a/68891371
    public_keys = {}
    for jwk in jwks_config["keys"]:
        kid = jwk["kid"]
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    try:
        headers = jwt.get_unverified_header(access_token)
        kid = headers["kid"]
        key = public_keys[kid]
        payload = jwt.decode(
            access_token, key=public_keys[kid], algorithms=[headers["alg"]]
        )
        # this comes from JWT documentation
        # https://pyjwt.readthedocs.io/en/stable/usage.html#expiration-time-claim-exp
        now = calendar.timegm(datetime.now(tz=timezone.utc).utctimetuple())
        return payload["exp"] - now > min_time
    except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
        logging.warning(f"Unable to open / expired token: {e}")
        return False

def generate_tokens(oidc_config, scopes, access_token_dir, token_ttl, secrets):
    for s in secrets:
        # not our thing
        if not isinstance(secrets[s], dict):
            continue
        token_file = os.path.join(access_token_dir, s)
        if not valid_token(token_file, oidc_config, token_ttl):
            logging.info("Token needs refreshing")
            with open(token_file, "w+") as f:
                f.write(
                    get_access_token(oidc_config["token_endpoint"], scopes, secrets[s])
                )
        else:
            logging.info("Token is still valid, not refreshing")


def main():
    logging.basicConfig()
    # get config from env
    checkin_secrets_file = os.environ["CHECKIN_SECRETS_FILE"]
    oidc_config_url = os.environ.get("CHECKIN_OIDC_URL", CHECKIN_OIDC_URL)
    oidc_config = requests.get(oidc_config_url).json()
    scopes = os.environ.get("CHECKIN_SCOPES", CHECKIN_SCOPES)
    access_token_dir = os.environ["ACCESS_TOKEN_DIR"]
    token_ttl = int(os.environ.get("ACCESS_TOKEN_TTL", ACCESS_TOKEN_TTL))
    secrets = read_secrets(checkin_secrets_file)
    generate_tokens(oidc_config, scopes, access_token_dir, token_ttl, secrets)


if __name__ == "__main__":
    main()
