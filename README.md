# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers.

## Site Configuration

This repository consists of the main configuration for the fedcloud catchall
operations. For every endpoint, a file in the `sites` directory should describe
its configuration with a format as follows:

```yaml
gocdb: <name in gocdb of the site>
endpoint: <keystone endpoint of the site>
# optional: use central image sync
images:
  # true, get sync, false do not
  sync: true
  # a list of supported formats of the site can be specified
  # if not available, no conversion will be done, so whatever format
  # is available in AppDB will be used
  formats:
    - qcow2
    - raw
# optionally specify a protocol for the Keystone V3 federation API
protocol: openid | oidc (default is openid)
# optionally specify a region name if using different regions
region: myregion
vos:
  # List of VOs defined as follows
  - name: <vo name>
    auth:
      project_id: <project id supporting the VO vo name at the site>
    # any other optional configuration for cloud-info-provider, e.g:
    # not really used for now
    defaultNetwork: private | public | private_only | public_only
    publicNetwork: <name of the public network>
```

## Docker containers

Components are run as docker containers, which if not available upstream, are
generated in this repository.

## Deployment

Deployment is managed with GitHub Actions, there is a VM for the
cloud-info-provider and one VM for the image sync. Check the [deploy](./deploy)
directory for details. Configuration is done with ansible using a
[dedicated role](./deploy/roles/catchall):

```sh
ansible-playbook -i inventory.yaml --extra-vars "@secrets.yaml" playbook.yaml
```

where:

- `inventory.yaml` contains the ansible inventory with the host to configure
- `secrets.yaml` contains the credentials for every configured VO and a valid
  token for the AMS
- `playbook.yaml` is an ansible playbook that just uses the `catchall` role to
  configure the host
