#!/bin/sh

# make sure we stop if there is any failing command
set -e

# We deal with OpenStack, no need to have anything else
CLOUD_INFO_MIDDLEWARE=openstack

export CHECKIN_SECRETS_FILE="$CHECKIN_SECRETS_PATH/secrets.yaml"

# use service account for everyone
export OS_DISCOVERY_ENDPOINT="https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration"
OS_CLIENT_ID="$(yq -r '.checkin.client_id' <"$CHECKIN_SECRETS_FILE")"
export OS_CLIENT_ID
OS_CLIENT_SECRET="$(yq -r '.checkin.client_secret' <"$CHECKIN_SECRETS_FILE")"
export OS_CLIENT_SECRET
export OS_ACCESS_TOKEN_TYPE="access_token"
export OS_AUTH_TYPE="v3oidcclientcredentials"
export OS_OPENID_SCOPE="openid profile eduperson_entitlement email entitlements"
cloud-info-provider-service \
	--middleware "$CLOUD_INFO_MIDDLEWARE" \
	--format glue21json "$SITE_CONFIG" >"$SITE_INFO_FILE"

# Publish to object
if test -s "$SITE_INFO_FILE"; then
	if test "$SWIFT_SITE_NAME" != ""; then
		ACCESS_TOKEN_FILE="$(mktemp)"
		token-generator $ACCESS_TOKEN_FILE
		OIDC_ACCESS_TOKEN=$(cat "$ACCESS_TOKEN_FILE")
		export OIDC_ACCESS_TOKEN
		export EGI_VO="$SWIFT_VO_NAME"
		SWIFT_URL=$(/fedcloud/bin/fedcloud openstack \
			--site "$SWIFT_SITE_NAME" \
			catalog show swift -f json |
			jq -r '(.endpoints[] | select(.interface=="public")).url')
		export RCLONE_CONFIG_REMOTE_TYPE="swift"
		export RCLONE_CONFIG_REMOTE_ENV_AUTH="false"
		export RCLONE_CONFIG_REMOTE_STORAGE_URL="$SWIFT_URL"
		eval "$(/fedcloud/bin/fedcloud site env --site "$SWIFT_SITE_NAME")"
		export RCLONE_CONFIG_REMOTE_AUTH_URL="$OS_AUTH_URL"
		OS_AUTH_TOKEN=$(/fedcloud/bin/fedcloud openstack \
			--site "$SWIFT_SITE_NAME" token issue -c id -f value)
		export RCLONE_CONFIG_REMOTE_AUTH_TOKEN="$OS_AUTH_TOKEN"
		rclone mkdir "remote:$SWIFT_CONTAINER_NAME"
		rclone copy "$SITE_INFO_FILE" "remote:$SWIFT_CONTAINER_NAME"
		echo "Upload completed!"
	fi
fi
