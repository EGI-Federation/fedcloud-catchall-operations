#!/bin/sh

set -e

# This may fail if the OS_AUTH_URL is not the one registered in GOC
GOCDB_ID=$(python -c "from __future__ import print_function; \
                      from cloud_info_provider.providers import gocdb; \
		      print(gocdb.find_in_gocdb('$GOCDB_URL', \
                                                '$GOCDB_SERVICE_TYPE')['gocdb_id'], end='')")

if test "x$AMS_TOKEN_FILE" != "x"; then
    AMS_TOKEN=$(cat "$AMS_TOKEN_FILE")
fi

AMS_TOPIC=SITE_${SITE_NAME}_ENDPOINT_${GOCDB_ID}

# exit if TOPIC is not available.
curl -f "https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC?key=$AMS_TOKEN" > /dev/null 2>&1 \
    || (echo "Topic $AMS_TOPIC is not avaiable, aborting!"; false)

# Other OS related parameter should be available as env variables
cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
                            --middleware "$CLOUD_INFO_MIDDLEWARE" \
                            --auth-refresher oidcvorefresh \
                            --oidc-credentials-path "$CHECKIN_SECRETS_PATH" \
                            --oidc-token-endpoint "$CHECKIN_OIDC_TOKEN" \
                            --format glue21 \
                            --publisher ams \
                            --ams-token "$AMS_TOKEN" \
                            --ams-topic "$AMS_TOPIC" \
                            --ams-host "$AMS_HOST"
