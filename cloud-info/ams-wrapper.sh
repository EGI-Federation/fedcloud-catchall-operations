#!/bin/sh

set -e

# This may fail if the OS_AUTH_URL is not the one registered in GOC
GOCDB_ID=$(python -c "from __future__ import print_function; \
                      from cloud_info_provider.providers import gocdb; \
                      print(gocdb.get_goc_info('$GOCDB_URL', \
                                               '$GOCDB_SERVICE_TYPE')['gocdb_id'], end='')")

if test "x$AMS_TOKEN_FILE" != "x"; then
    export AMS_TOKEN=$(cat $AMS_TOKEN_FILE)
fi

export AMS_TOPIC=SITE_${SITE_NAME}_ENDPOINT_${GOCDB_ID}

# exit if TOPIC is not available.
curl -f https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC\?key\=$AMS_TOKEN > /dev/null 2>&1 \
    || (echo "Topic $AMS_TOPIC is not avaiable, aborting!"; false)

exec /usr/local/bin/cloud-info-wrapper.sh
