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


# Any OS related parameter should be available as env variables
if test "$CHECKIN_SECRETS_PATH" = ""; then
    cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                                --middleware "$CLOUD_INFO_MIDDLEWARE" \
                                --ignore-share-errors \
                                --format glue21 > cloud-info.out
else
    cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                                --middleware "$CLOUD_INFO_MIDDLEWARE" \
                                --ignore-share-errors \
                                --auth-refresher oidcvorefresh \
                                --oidc-credentials-path "$CHECKIN_SECRETS_PATH" \
                                --oidc-token-endpoint "$CHECKIN_OIDC_TOKEN" \
                                --oidc-scopes "openid email profile eduperson_entitlement" \
                                --format glue21 > cloud-info.out
fi

# Publishing on our own as message is too large for some providers
ARGO_URL="https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC:publish?key=$AMS_TOKEN"

printf '{"messages":[{"attributes":{},"data":"' > ams-payload
grep -v "UNKNOWN" cloud-info.out | grep -v "^#" | gzip | base64 -w 0 >> ams-payload
printf '"}]}' >> ams-payload

curl -X POST "$ARGO_URL" -H "content-type: application/json" -d @ams-payload
