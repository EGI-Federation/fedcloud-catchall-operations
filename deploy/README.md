# EGI Cloud Catch-all operations deployment

This directory manages the deployment automatically on selected providers of
the infrastructure

## Deployment

Deployment is performed in 2 phases:

1. Terraforming the VM where the cloud-info-provider is run
1. Configuring the VM with ansible to run the cloud-info-provider

Everything is managed automatically via GitHub actions, on pull-requests
the terraform plan is updated and when merging, it's applied and
ansible is run on the resulting infrastructure.

### Secrets

Secrets are stored in GitHub. These include:
- `ANSIBLE_SECRETS`: `yaml` file with robot account credentials and AMS token
  for pushing messages
- `APP_ID` and `APP_PRIVATE_KEY`: credentials for GitHub app capable of
  getting a token to pull the repo at the deployed VM
- `CHECKIN_CLIENT_ID`, `CHECKIN_CLIENT_SECRET` and `CHECKIN_REFRESH_TOKEN` with
  valid Check-in credentials for deployment of the VM on the provider
