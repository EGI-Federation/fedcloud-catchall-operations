# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers.
This is a set of docker containers and an ansible role to operate the
federation components of the EGI Cloud Compute service.

## Implementation

This repo consists of an ansible playbook that creates:
- a configuration directory `/etc/fedcloud/vos/<vo>` for every VO
  that will contain credentials to authenticate with that VO
- a cloud-info-provider configuration per site that takes
  credential info from `/etc/fedcloud/vos/<vo>` and sends information
  to the AMS queue
- a cron job per site that will execute the cloud-info-provider for every
  vo supported by the site and push the information to the AMS in order
  to be consumed by clients.

Sites are configred following the YAML files of the `sites` directory.
There is a file per site that looks like this:

```yaml
gocdb_site: <name in gocdb of the site>
endpoint: <keystone endpoint of the site>
# optionally specify a protocol for the Keystone V3 federation API
protocol: openid | oidc (default is openid)
vos:
   <vo name>:
     auth:
       project_id: <project id supporting the VO vo name at the site>
     # any other optional configuration for cloud-info-provider, e.g:
     defaultNetwork: private | public | private_only | public_only
     publicNetwork: <name of the public network>
```


## Deployment

```sh
ansible-playbook -i inventory.yaml --extra-vars "@secrets.yaml" playbook.yaml
```

where:

- `inventory.yaml` contains the ansible inventory with the host to configure
- `secrets.yaml` contains the credentials for every configured VO and
  a valid token for the AMS
- `playbook.yaml` is an ansible playbook that just uses the `fedcloud-catchall-ops`
  role to configure the host

### Configuration

The role expects the following variables to be defined:

- `vos` a map that contains entry for each VO with the Check-in credentials:
  ```yaml
  <vo name>:
    auth:
      client_id: <checkin client id>
      client_secret: <checkin client secret>
      refresh_token: <checkin refresh token>
  ```

- `ams_project`: name of the AMS project to use (default `egi_cloud_info`)
- `ams_host`: name of the AMS host (default `msg.argo.grnet.gr`)
- `ams_token`: secret to use to connect to AMS
- `cloud_info_image`: docker image for the cloud-info-provider
  (default `egifedcloud/ops-cloud-info:latest`)
