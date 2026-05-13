#!/bin/bash
# Configures the environment for the actual deployment
# Expects to have in the environment:
# CLIENT_ID, CLIENT_SECRET: a valid client id and secret for service account
# in Check-in
# Receives as parameter the directory where deployment configuration is
# stored (deploy/cloud-info or deploy/image-sync)

WORKDIR="$1"
pushd "$WORKDIR"

# We fake here the github env
GITHUB_ENV="${GITHUB_ENV:-/dev/null}"

echo "::debug::Getting a token from Check-in"
# using parametric scopes to only have access to cloud.egi.eu VO
SCOPE="openid%20email%20profile%20voperson_id"
SCOPE="$SCOPE%20eduperson_entitlement:urn:mace:egi.eu:group:cloud.egi.eu:role=vm_operator#aai.egi.eu"
SCOPE="$SCOPE%20eduperson_entitlement:urn:mace:egi.eu:group:cloud.egi.eu:role=member#aai.egi.eu"
SCOPE="$SCOPE%20entitlements:urn:mace:egi.eu:group:cloud.egi.eu:role=vm_operator#aai.egi.eu"
SCOPE="$SCOPE%20entitlements:urn:mace:egi.eu:group:cloud.egi.eu:role=member#aai.egi.eu"
OIDC_TOKEN=$(curl -X POST "https://aai.egi.eu/auth/realms/egi/protocol/openid-connect/token" \
                  -d "grant_type=client_credentials&client_id=$CLIENT_ID&scope=$SCOPE&client_secret=$CLIENT_SECRET" \
                | jq -r ".access_token")
echo "::add-mask::$OIDC_TOKEN"
echo "::debug::Token obtained!"
cp ../clouds.yaml .
BACKEND_SITE="$(yq -r .clouds.backend.site clouds.yaml)"
BACKEND_VO="$(yq -r .clouds.backend.vo clouds.yaml)"
EGI_SITE="$(yq -r .clouds.deploy.site clouds.yaml)"
DEPLOY_VO="$(yq -r .clouds.deploy.vo clouds.yaml)"
echo "::debug::Deploying at $EGI_SITE (vo: $DEPLOY_VO), \
	backend at $BACKEND_SITE (vo: $BACKEND_VO)"
echo "EGI_SITE=$EGI_SITE" >> "$GITHUB_ENV"
set -x
uv run fedcloud openstack token issue --oidc-access-token "$OIDC_TOKEN" \
	--site "$BACKEND_SITE" --vo "$BACKEND_VO" -j > .fedcloud-output
echo "::debug::$(cat .fedcloud-output)"
BACKEND_OS_TOKEN=$(jq -r '.[0].Result.id' < .fedcloud-output)"
echo "::add-mask::$BACKEND_OS_TOKEN"
sed -i -e "s/backend_secret/$BACKEND_OS_TOKEN/" clouds.yaml
DEPLOY_OS_TOKEN="$(uv run fedcloud openstack token issue \
	--oidc-access-token "$OIDC_TOKEN" \
        --site "$EGI_SITE" --vo "$DEPLOY_VO" -j | jq -r '.[0].Result.id')"
echo "::add-mask::$DEPLOY_OS_TOKEN"

echo "::debug::Preparing OpenStack configuration for sites"
sed -i -e "s/deploy_secret/$DEPLOY_OS_TOKEN/" clouds.yaml
mkdir -p ~/.config/openstack
touch ~/.config/openstack/secure.yaml
FEDCLOUD_LOCKER_TOKEN="$(uv run fedcloud secret locker create \
                         --oidc-access-token "$OIDC_TOKEN" \
                         --ttl 1h --num-uses 2)"
echo "::add-mask::$FEDCLOUD_LOCKER_TOKEN"
uv run fedcloud secret put --locker-token "$FEDCLOUD_LOCKER_TOKEN" \
	deploy "data=$ANSIBLE_SECRETS"
echo "FEDCLOUD_LOCKER_TOKEN=$FEDCLOUD_LOCKER_TOKEN" >> "$GITHUB_ENV"

echo "::debug::Secret created!"
