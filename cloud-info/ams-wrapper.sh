#!/bin/sh

set -e

# This may fail if the OS_AUTH_URL is not the one registered in GOC
GOCDB_ID=$(python -c "from __future__ import print_function; \
                      from cloud_info_provider.providers import gocdb; \
                      print(gocdb.get_goc_info('$OS_AUTH_URL', \
                                               'org.openstack.nova')['gocdb_id'], end='')")


if test "x$AMS_TOKEN_FILE" != "x"; then
    AMS_TOKEN=$(cat $AMS_TOKEN_FILE)
fi


cat > /etc/ams-clipw.settings << EOF
[AMS]
ams_host: msg-devel.argo.grnet.gr 
ams_project: $AMS_PROJECT
ams_topic: SITE_${SITE_NAME}_ENDPOINT_${GOCDB_ID}
msg_file_path:
info_provider_path: /usr/local/bin/cloud-info-wrapper.sh 

[AUTH]
token: $AMS_TOKEN
cert_path: $AMS_CERT_PATH
key_path: $AMS_KEY_PATH
EOF

ams-clipw -c /etc/ams-clipw.settings
