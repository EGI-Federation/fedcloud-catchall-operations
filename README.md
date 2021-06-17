# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers.

## Site Configuration

This repo consists of the main configuration for the fedcloud
catchall operations. For every endpoint, a file in the `sites`
directory should describe its configuration with a format as
follows:

```yaml
gocdb: <name in gocdb of the site>
endpoint: <keystone endpoint of the site>
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
  defaultNetwork: private | public | private_only | public_only
  publicNetwork: <name of the public network>
```

## Docker containers

Componets are run as docker containers, which if not available
upstream, are generated in this repo.

## Deployment

Deployment is managed on a separate private repository that includes
several secrets. Deployment is done with ansible using a [dedicated
role](https://github.com/EGI-Federation/ansible-role-fedcloud-ops) with:

```sh
ansible-playbook -i inventory.yaml --extra-vars "@secrets.yaml" playbook.yaml
```

where:

- `inventory.yaml` contains the ansible inventory with the host to configure
- `secrets.yaml` contains the credentials for every configured VO and
  a valid token for the AMS
- `playbook.yaml` is an ansible playbook that just uses the `fedcloud-catchall-ops`
  role to configure the host
