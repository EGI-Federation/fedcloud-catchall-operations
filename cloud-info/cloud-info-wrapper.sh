#!/bin/sh

CLIENT_ID=$(cat $CHECKIN_CLIENT_ID_FILE)
CLIENT_SECRET=$(cat $CHECKIN_CLIENT_SECRET_FILE)
REFRESH_TOKEN=$(cat $CHECKIN_REFRESH_TOKEN_FILE)

export OS_ACCESS_TOKEN=$(curl -s -X POST -u $CLIENT_ID:$CLIENT_SECRET \
    -d "client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET&grant_type=refresh_token&refresh_token=$REFRESH_TOKEN&scope=openid" \
    https://aai.egi.eu/oidc/token | jq -r ".access_token")

# Other OS related parameter should be available as env variables
cloud-info-provider-service --yaml-file $CLOUD_INFO_CONFIG \
                            --middleware openstack \
                            --format glue21
