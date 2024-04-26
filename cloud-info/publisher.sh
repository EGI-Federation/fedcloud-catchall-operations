#!/bin/sh

set -e

# OpenStack
export GOCDB_URL="$OS_AUTH_URL"
export GOCDB_SERVICE_TYPE=org.openstack.nova
export CLOUD_INFO_MIDDLEWARE=openstack

ams-wrapper.sh

if [ -n "$OCCI_ENDPOINT" ]; then
	# OCCI
	export GOCDB_URL="$OCCI_ENDPOINT"
	export GOCDB_SERVICE_TYPE=eu.egi.cloud.vm-management.occi
	export CLOUD_INFO_MIDDLEWARE=ooi
	ams-wrapper.sh
fi
