#!/bin/sh
# Configure current host with ansible
# Expects as arguments the OAUTH_TOKEN, the COMMIT_SHA and the SLACK_WEBHOOK_URL

set -e

OAUTH_TOKEN="$1"
COMMIT_SHA="$2"
SHORT_SHA="$3"
SLACK_WEBHOOK_URL="$4"

ansible-galaxy install git+https://github.com/EGI-Foundation/ansible-role-fedcloud-ops.git

# Configure!
if ansible-playbook -i inventory.yaml  \
       --extra-vars @secrets.yaml \
       --extra-vars @extra-vars.yaml \
       --extra-vars @vos.yaml \
       --extra-vars "cloud_info_image=egifedcloud/ops-cloud-info:sha-$SHORT_SHA"
       playbook.yaml >ansible.log 2>&1 ; then
   status_summary="success"
   color="#6DBF59"
   header="Successful deployment :rocket:"
else
   status_summary="fail"
   color="#EA4F47"
   header="Failed deployment :boom:"
fi

GITHUB_COMMIT_URL="https://api.github.com/repos/EGI-Foundation/fedcloud-catchall-operations/commits/$COMMIT_SHA/pulls"

# Find out PR we need to update
ISSUE_NUMBER=$(curl \
                 -H "Authorization: token $OAUTH_TOKEN" \
                 -H "Accept: application/vnd.github.groot-preview+json" \
                 "$GITHUB_COMMIT_URL" | jq .[0].number)

GITHUB_ISSUE_URL="https://api.github.com/repos/EGI-Foundation/fedcloud-catchall-operations/issues/$ISSUE_NUMBER/comments"

{
  echo "### Ansible deployment: \`$status_summary\`"
  echo '<details><summary>Deployment log</summary>'
  echo
  echo '```'
  cat ansible.log
  echo '```'
  echo
  echo '</details>'
} > github_body.txt
echo "{}" | jq --arg b "$(cat github_body.txt)" '{body: $b}' > github_body.json

# Let GitHub know
comment_url=$(curl -X POST \
                -H "Authorization: token $OAUTH_TOKEN" \
                -H "Accept: application/vnd.github.v3+json" \
                "$GITHUB_ISSUE_URL" \
                --data @github_body.json | \
              jq -r .html_url)

cat > slack_body.json << EOF
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
            "text": "fedcloud-catchall-operations deployment was completed for <$comment_url| PR \`#$ISSUE_NUMBER\`> "
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
