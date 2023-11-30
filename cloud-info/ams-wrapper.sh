#!/bin/sh

set -e

# This may fail if the OS_AUTH_URL is not the one registered in GOC
GOCDB_ID=$(python -c "from __future__ import print_function; \
                      from cloud_info_provider.providers import gocdb; \
                      print(gocdb.find_in_gocdb('$GOCDB_URL', \
                                                '$GOCDB_SERVICE_TYPE',
                                                timeout=60)['gocdb_id'], end='')")

if test "$AMS_TOKEN_FILE" != ""; then
    AMS_TOKEN=$(cat "$AMS_TOKEN_FILE")
elif test "$HOSTCERT" != "" -a  "$HOSTKEY" != ""; then
    AMS_TOKEN=$(python -c "from argo_ams_library import ArgoMessagingService; \
			   ams = ArgoMessagingService(endpoint='$AMS_HOST', \
                                                      project='$AMS_PROJECT', \
                                                      cert='$HOSTCERT', \
                                                      key='$HOSTKEY'); \
                           print(ams.token)")
fi

if test "$SITE_NAME" = ""; then
    SITE_NAME="$(yq -r .site.name "$CLOUD_INFO_CONFIG" | tr "." "-")"
fi

SITE_TOPIC=$(echo "$SITE_NAME" | tr "." "-")
AMS_TOPIC="SITE_${SITE_TOPIC}_ENDPOINT_${GOCDB_ID}"

# exit if TOPIC is not available.
curl -f "https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC?key=$AMS_TOKEN" > /dev/null 2>&1 \
    || (echo "Topic $AMS_TOPIC is not avaiable, aborting!"; false)


# Attempt to generate the site configuration
AUTO_CONFIG_PATH="$(mktemp -d)"

# First get valid access token
export CHECKIN_SECRETS_FILE="$CHECKIN_SECRETS_PATH/secrets.yaml"
# TODO(enolfc): avoid creating new tokens for every provider
export ACCESS_TOKEN_FILE="$AUTO_CONFIG_PATH/token.yaml"
USE_ACCESS_TOKEN=0
if token-generator; then
    # TODO(enolfc): even if this belows fails, we should use access token as it will provide
    # access to more projects
    if SECRETS_FILE="$ACCESS_TOKEN_FILE" config-generator > "$AUTO_CONFIG_PATH/site.yaml"; then
        # this worked, let's update the env
        export CHECKIN_SECRETS_PATH="$AUTO_CONFIG_PATH/vos"
        export CLOUD_INFO_CONFIG="$AUTO_CONFIG_PATH/site.yaml"
        USE_ACCESS_TOKEN=1
    fi
fi

# Any OS related parameter should be available as env variables
if test "$CHECKIN_SECRETS_PATH" = ""; then
    # Case 1: manual config
    cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                                --middleware "$CLOUD_INFO_MIDDLEWARE" \
                                --ignore-share-errors \
                                --format glue21 > cloud-info.out
elif test "$USE_ACCESS_TOKEN" -eq 1; then
    # Case 2: access token style
    cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                                --middleware "$CLOUD_INFO_MIDDLEWARE" \
                                --ignore-share-errors \
                                --auth-refresher accesstoken \
                                --format glue21 > cloud-info.out
else
    # Let's use the service account directly on the info provider
    CHECKIN_DISCOVERY="https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration"
    CLIENT_ID="$(yq -r '.fedcloudops.client_id' < $CHECKIN_SECRETS_FILE)"
    CLIENT_SECRET="$(yq -r '.fedcloudops.client_secret' < $CHECKIN_SECRETS_FILE)"
    cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                                --middleware "$CLOUD_INFO_MIDDLEWARE" \
                                --ignore-share-errors \
                                --os-auth-type v3oidcclientcredentials \
				--os-discovery-endpoint "$CHECKIN_DISCOVERY" \
				--os-client-id "$CLIENT_ID" \
				--os-client-secret "$CLIENT_SECRET" \
				--os-access-token-type access_token \
				--os-openid-scope "openid profile eduperson_entitlement email" \
                                --format glue21 > cloud-info.out
fi

# Fail if there are no shares
grep -q GLUE2ShareID cloud-info.out \
    || (echo "No share information available, aborting!"; false)

# Publishing on our own as message is too large for some providers
ARGO_URL="https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC:publish?key=$AMS_TOKEN"

printf '{"messages":[{"attributes":{},"data":"' > ams-payload
grep -v "UNKNOWN" cloud-info.out | grep -v "^#" | grep -v ": $" | gzip | base64 -w 0 >> ams-payload
printf '"}]}' >> ams-payload

curl -X POST "$ARGO_URL" -H "content-type: application/json" -d @ams-payload

rm -rf "$VO_CONFIG_PATH"
