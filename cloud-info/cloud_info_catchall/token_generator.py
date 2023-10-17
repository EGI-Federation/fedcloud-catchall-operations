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
from datetime import datetime, timezone

import jwt
import requests
import yaml

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


def valid_token(token, oidc_config, min_time):
    if not token:
        return False
    jwks_config = requests.get(oidc_config["jwks_uri"]).json()
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


def generate_tokens(oidc_config, scopes, tokens, token_ttl, secrets):
    new_tokens = {}
    for s in secrets:
        # not our thing
        if not isinstance(secrets[s], dict):
            continue
        token = tokens.get(s, {}).get("access_token", None)
        if not valid_token(token, oidc_config, token_ttl):
            logging.info("Token needs refreshing")
            token = get_access_token(oidc_config["token_endpoint"], scopes, secrets[s])
        else:
            logging.info("Token is still valid, not refreshing")
        new_tokens[s] = {"access_token": token}
    return new_tokens


def main():
    logging.basicConfig()
    # get config from env
    checkin_secrets_file = os.environ["CHECKIN_SECRETS_FILE"]
    oidc_config_url = os.environ.get("CHECKIN_OIDC_URL", CHECKIN_OIDC_URL)
    oidc_config = requests.get(oidc_config_url).json()
    scopes = os.environ.get("CHECKIN_SCOPES", CHECKIN_SCOPES)
    access_token_file = os.environ["ACCESS_TOKEN_FILE"]
    token_ttl = int(os.environ.get("ACCESS_TOKEN_TTL", ACCESS_TOKEN_TTL))
    secrets = read_secrets(checkin_secrets_file)
    tokens = {}
    if os.path.exists(access_token_file):
        tokens.update(read_secrets(access_token_file))
    new_tokens = generate_tokens(oidc_config, scopes, tokens, token_ttl, secrets)
    with open(access_token_file, "w+") as f:
        f.write(yaml.dump(new_tokens))


if __name__ == "__main__":
    main()
