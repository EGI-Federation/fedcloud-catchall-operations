#!/bin/sh
# Configure current host with ansible
# Expects as arguments:
# - a GitHub OAUTH_TOKEN to update the PR
# - the COMMIT_SHA
# - a locker for fedcloud secret to obtain the secrets
# - tags for the ansible configuration
# - the SHORT_SHA used for pulling the docker image to use
# - a SLACK_WEBHOOK_URL to report on the status
set -e

OAUTH_TOKEN="$1"
COMMIT_SHA="$2"
FEDCLOUD_SECRET_LOCKER="$3"
TAGS="$4"
SHORT_SHA="$5"
SLACK_WEBHOOK_URL="$6"

# create a virtual env for fedcloudclient
python3 -m venv "$PWD/.venv"
"$PWD/.venv/bin/pip" install fedcloudclient

TMP_SECRETS="$(mktemp)"
"$PWD/.venv/bin/fedcloud" secret get --locker-token "$FEDCLOUD_SECRET_LOCKER" \
	deploy data >"$TMP_SECRETS" && mv "$TMP_SECRETS" secrets.yaml

cat >>extra-vars.yaml <<EOF
cloud_info_image: "ghcr.io/egi-federation/fedcloud-cloud-info:sha-$SHORT_SHA"
image_sync_image: "ghcr.io/egi-federation/fedcloud-image-sync:sha-$SHORT_SHA"
site_config_dir: "$(readlink -f ../sites)"
EOF

# get access token for motley-cue
CLIENT_ID=$(yq -r '.checkin.client_id' <secrets.yaml)
CLIENT_SECRET=$(yq -r '.checkin.client_secret' <secrets.yaml)
SCOPE="openid%20email%20profile%20voperson_id"
SCOPE="$SCOPE%20eduperson_entitlement:urn:mace:egi.eu:group:cloud.egi.eu:role=vm_operator#aai.egi.eu"
SCOPE="$SCOPE%20eduperson_entitlement:urn:mace:egi.eu:group:cloud.egi.eu:role=member#aai.egi.eu"
SCOPE="$SCOPE%20entitlements:urn:mace:egi.eu:group:cloud.egi.eu:role=member#aai.egi.eu"
SCOPE="$SCOPE%20entitlements:urn:mace:egi.eu:group:cloud.egi.eu:role=member#aai.egi.eu"
ACCESS_TOKEN=$(curl --request POST "https://aai.egi.eu/auth/realms/egi/protocol/openid-connect/token" \
	--data "grant_type=client_credentials&client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET&scope=$SCOPE" |
	jq -r ".access_token")

# use pip-installed Ansible (apt version is too old)
# in a separate venv and set PATH for it
python3 -m venv "$PWD/.ansible"
"$PWD/.ansible/bin/pip" install ansible
export PATH="$PWD/.ansible/bin:$PATH"

# install Ansible dependencies
ansible-galaxy role install -r galaxy-requirements.yaml

# Configure!
if ansible-playbook -i inventory.yaml \
	--extra-vars @secrets.yaml \
	--extra-vars @extra-vars.yaml \
	--extra-vars ACCESS_TOKEN="$ACCESS_TOKEN" \
	--tags "$TAGS" \
	playbook.yaml >ansible.log 2>&1; then
	status_summary="success"
	color="#6DBF59"
	header="Successful deployment :rocket:"
else
	status_summary="fail"
	color="#EA4F47"
	header="Failed deployment :boom:"
fi

# This is a temporary way to get the auto discovery working while we transition for all sites
# copy the secrets to the /etc/egi/vos dir which is readable from the containers
cp secrets.yaml /etc/egi/vos/secrets.yaml

# make sure the container user (1999) can access the files
chown -R 1999:1999 /etc/egi/

GITHUB_COMMIT_URL="https://api.github.com/repos/EGI-Federation/fedcloud-catchall-operations/commits/$COMMIT_SHA/pulls"

# Find out PR we need to update
ISSUE_NUMBER=$(curl \
	-H "Accept: application/vnd.github.groot-preview+json" \
	"$GITHUB_COMMIT_URL" | jq .[0].number)

GITHUB_ISSUE_URL="https://api.github.com/repos/EGI-Federation/fedcloud-catchall-operations/issues/$ISSUE_NUMBER/comments"

{
	echo "### Ansible deployment: \`$status_summary\`"
	echo '<details><summary>Deployment log</summary>'
	echo
	echo '```'
	cat ansible.log
	echo '```'
	echo
	echo '</details>'
} >github_body.txt
echo "{}" | jq --arg b "$(cat github_body.txt)" '{body: $b}' >github_body.json

# Let GitHub know
comment_url=$(curl -X POST \
	-H "Authorization: token $OAUTH_TOKEN" \
	-H "Accept: application/vnd.github.v3+json" \
	"$GITHUB_ISSUE_URL" \
	--data @github_body.json |
	jq -r .html_url)

cat >slack_body.json <<EOF
{
  "attachments": [
    {
      "color": "$color",
      "blocks": [
        {
          "type": "header",
          "text": {
            "type": "plain_text",
            "text": "$header",
            "emoji": true
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "fedcloud-catchall deployment was completed for <$comment_url| PR \`#$ISSUE_NUMBER\`> "
          }
        }
      ]
    }
  ]
}
EOF

# Let Slack know
curl -X POST -H 'Content-type: application/json' \
	--data @slack_body.json \
	"$SLACK_WEBHOOK_URL"
