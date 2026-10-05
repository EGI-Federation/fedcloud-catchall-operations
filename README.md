# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers.

## Site Configuration

This repository consists of the main configuration for the fedcloud catchall
operations. For every endpoint, a file in the `sites` directory should describe
its configuration with a format as follows:

```yaml
gocdb: <name in gocdb of the site>
endpoint: <keystone endpoint of the site>
# optional: set authentication type - sites are expected to support direct
# usage of Check-in access tokens, so default here is v3oidcaccesstoken
# if those tokens are not supported set v3applicationcredential with the
# credentials stored in the EGI Secret Store as detailed below
# auth_type: v3oidcaccesstoken
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

## Authentication

All components rely on
`[keystoneauth](https://opendev.org/openstack/keystoneauth)` for authentication,
thus can use different authentication methods. By default, we assume that the
site supports a valid Check-in access token through the
`[v3oidcaccesstoken](https://docs.openstack.org/keystoneauth/latest/plugin-options.html#v3oidcaccesstoken)`
with `protocol` equal to `openid` and `identity-provider` equal to `egi.eu`. A
valid access token will be obtained for every execution of the components.

If the site does not support direct usage of those tokens, set `auth_type` to
`v3applicationcredentials`. The code will then try to find a set of valid
`application credentials` in EGI's secret store at
`/secrets/users/<service account id>/cloudmon/<keystone host name>/<vo name>`.
The secret store is accessed using a valid Check-n access token.

## Docker containers

Components are run as containers, which if not available upstream, are generated
in this repository.

## Deployment

Deployment is managed with GitHub Actions, there is a VM for the
cloud-info-provider and one VM for the image sync. Check the [deploy](./deploy)
directory for details. Configuration is done with Ansible using a
[dedicated role](./deploy/roles/catchall):

```sh
ansible-playbook -i inventory.yaml --extra-vars "@secrets.yaml" playbook.yaml
```

where:

- `inventory.yaml` contains the Ansible inventory with the host to configure
- `secrets.yaml` contains the credentials for every configured VO and a valid
  token for the AMS
- `playbook.yaml` is an Ansible playbook that just uses the `catchall` role to
  configure the host
