#!/bin/sh

set -e

# This may fail if the OS_AUTH_URL is not the one registered in GOC
GOCDB_ID=$(python -c "from __future__ import print_function; \
                      from cloud_info_provider.providers import gocdb; \
                      print(gocdb.find_in_gocdb('$GOCDB_URL', \
                                                '$GOCDB_SERVICE_TYPE',
                                                timeout=60)['gocdb_id'], end='')")

# Attempt to generate the site configuration
AUTO_CONFIG_PATH="$(mktemp -d)"

# First get valid access token
export CHECKIN_SECRETS_FILE="$CHECKIN_SECRETS_PATH/secrets.yaml"
# TODO(enolfc): avoid creating new tokens for every provider
export ACCESS_TOKEN_FILE="$AUTO_CONFIG_PATH/token.yaml"
if token-generator; then
	# TODO(enolfc): even if this belows fails, we should use access token as it will provide
	# access to more projects
	if SECRETS_FILE="$ACCESS_TOKEN_FILE" config-generator >"$AUTO_CONFIG_PATH/site.yaml"; then
		# this worked, let's update the env
		export CHECKIN_SECRETS_PATH="$AUTO_CONFIG_PATH/vos"
		export CLOUD_INFO_CONFIG="$AUTO_CONFIG_PATH/site.yaml"
	fi
fi

# Any OS related parameter should be available as env variables
if test "$CHECKIN_SECRETS_PATH" = ""; then
	# Case 1: manual config
	cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
		--middleware "$CLOUD_INFO_MIDDLEWARE" \
		--ignore-share-errors \
		--format glue21 >cloud-info.out
else
	# use service account for everyone
	export OS_DISCOVERY_ENDPOINT="https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration"
	OS_CLIENT_ID="$(yq -r '.checkin.client_id' <"$CHECKIN_SECRETS_FILE")"
	export OS_CLIENT_ID
	OS_CLIENT_SECRET="$(yq -r '.checkin.client_secret' <"$CHECKIN_SECRETS_FILE")"
	export OS_CLIENT_SECRET
	export OS_ACCESS_TOKEN_TYPE="access_token"
	export OS_AUTH_TYPE="v3oidcclientcredentials"
	export OS_OPENID_SCOPE="openid profile eduperson_entitlement email"
	cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
		--middleware "$CLOUD_INFO_MIDDLEWARE" \
		--ignore-share-errors \
		--format glue21 >cloud-info.out
	# Produce the json output also
	cloud-info-provider-service --yaml-file "$CLOUD_INFO_CONFIG" \
		--middleware "$CLOUD_INFO_MIDDLEWARE" \
		--ignore-share-errors \
		--format glue21json >site.json
fi

# Fail if there are no shares
grep -q GLUE2ShareID cloud-info.out ||
	(
		echo "No share information available, aborting!"
		false
	)

# Publish to AMS
if test "$AMS_TOKEN_FILE" != ""; then
	AMS_TOKEN=$(cat "$AMS_TOKEN_FILE")
elif test "$HOSTCERT" != "" -a "$HOSTKEY" != ""; then
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
curl -f "https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC?key=$AMS_TOKEN" >/dev/null 2>&1 &&
	(
		# Publishing on AMS on our own to ensure message fits

		ARGO_URL="https://$AMS_HOST/v1/projects/$AMS_PROJECT/topics/$AMS_TOPIC:publish?key=$AMS_TOKEN"

		printf '{"messages":[{"attributes":{},"data":"' >ams-payload
		grep -v "UNKNOWN" cloud-info.out | grep -v "^#" | grep -v ": $" | gzip | base64 -w 0 >>ams-payload
		printf '"}]}' >>ams-payload

		curl -X POST "$ARGO_URL" -H "content-type: application/json" -d @ams-payload
	)

# Publish to object
if [ -f site.json ]; then
	# Put this info into S3, configure rclone config with
	# a provider named "s3" using env variables
	export RCLONE_CONFIG_S3_TYPE=s3
	RCLONE_CONFIG_S3_ACCESS_KEY_ID="$(yq -r '.s3.access_key_id' <"$CHECKIN_SECRETS_FILE")"
	export RCLONE_CONFIG_S3_ACCESS_KEY_ID
	RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="$(yq -r '.s3.secret_access_key' <"$CHECKIN_SECRETS_FILE")"
	export RCLONE_CONFIG_S3_SECRET_ACCESS_KEY
	RCLONE_CONFIG_S3_ENDPOINT="$(yq -r '.s3.endpoint' <"$CHECKIN_SECRETS_FILE")"
	export RCLONE_CONFIG_S3_ENDPOINT
	S3_BUCKET_NAME="$(yq -r '.s3.bucket' <"$CHECKIN_SECRETS_FILE")"
	export S3_BUCKET_NAME
	RCLONE_CONFIG_S3_PROVIDER="$(yq -r '.s3.provider' <"$CHECKIN_SECRETS_FILE")"
	export RCLONE_CONFIG_S3_PROVIDER
	export RCLONE_CONFIG_S3_ACL=private
	export RCLONE_CONFIG_S3_NO_CHECK_BUCKET=true
	rclone copy site.json "s3:$S3_BUCKET_NAME/$SITE_NAME"
fi

rm -rf "$VO_CONFIG_PATH"
