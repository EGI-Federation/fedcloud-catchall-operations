#!/bin/sh

EXTRA_OPTS=""

if [ -n "$DEBUG" ]; then
    EXTRA_OPTS="$EXTRA_OPTS --debug"
fi

# Other OS related parameter should be available as env variables
cloud-info-provider-service --yaml-file $CLOUD_INFO_CONFIG \
                            --middleware $CLOUD_INFO_MIDDLEWARE \
                            --auth-refresher oidcvorefresh \
                            --oidc-credentials-path $CHECKIN_SECRETS_PATH \
                            --oidc-token-endpoint $CHECKIN_OIDC_TOKEN \
                            --format glue21 $EXTRA_OPTS
