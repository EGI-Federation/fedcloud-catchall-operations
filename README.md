# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers. 
This is a helm chart that will deploy the catchall operations for
the EGI federated cloud.

## What this does?

The chart will create:
- a cron job per site that will execute the cloud-info-provider for every 
  vo supporteb by the site and push the information to the AMS in order
  to be consumed by clients.

## Installing the chart

helm install -f sites.yaml -f secrets.yaml --name fedcloud fedcloud-ops

## Configuration

| Parameter                    | Description                                          | Default               |
|------------------------------|------------------------------------------------------|-----------------------|
| `sites`                      | A description of the sites to support                | `{}`                  |
| `auth.clientId`              | Check-in client id                                   |                       |
| `auth.clientSecret`          | Check-in client secret                               |                       |
| `auth.refreshToken`          | Check-in refresh token                               |                       |
| `cloudInfo.schedule`         | CronJob schedule of cloud-info                       | `*/5 * * * *`         |
| `cloudInfo.image.repository` | cloud-info image repository                          | `enolfc/cloudinfoops` |
| `cloudInfo.image.tag`        | cloud-info image tag                                 | `0.0.8`               |
| `cloudInfo.image.pullPolicy` | cloud-info image pull policy                         | `IfNotPresent`        |
| `cloudInfo.ams.project`      | cloud-info project name in AMS                       | `egi_cloud_info`      |
| `cloudInfo.ams.token`        | AMS token                                            |                       |
| `cloudInfo.ams.cert`         | AMS host cert (alternative to `cloudInfo.ams.token`) |                       |
| `cloudInfo.ams.key`          | AMS host key                                         |                       |

### Format of `sites`

```
sites:
  # This should be a dict of sites as follows:
  Name-of-site:
    endpoint: https://thekeystone-url/v3
    vos:
      # a new dict with name of the VO as key
      vo1:
        auth:
          # the id of the project
          project: xxx
        defaultNetwork: private | public | private_only | public_only (default is public)
        publicNetwork: <name of the public network> (default is UNKNOWN)
```
