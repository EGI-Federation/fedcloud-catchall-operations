# fedcloud-catchall-operations

Operation of fedcloud integration components for selected providers. 
This is a helm chart that will deploy the catchall operations for
the EGI federated cloud.

## What this does?

The chart will create:
- a cron job per site that will execute the cloud-info-provider for every 
  vo supporteb by the site and push the information to the AMS in order
  to be consumed by clients.
- a service per site and VO that will execute cloudkeeper-os to synchronise
  images pushed by cloudkeeper cron.
- a cron job per site and VO that executes cloudkeeper with the cloudkeeper-os
  service as backend to fetch the VO-wide image list from AppDB.

## Installing the chart

helm install -f sites.yaml -f secrets.yaml --name fedcloud fedcloud-ops

## Configuration

| Parameter                        | Description                                          | Default                   |
|----------------------------------|------------------------------------------------------|---------------------------|
| `sites`                          | A description of the sites to support                | `{}`                      |
| `cloudInfo.debug`                | Enable debug of cloud-info-provider                  | `false`                   |
| `cloudInfo.schedule`             | CronJob schedule of cloud-info                       | `*/5 * * * *`             |
| `cloudInfo.image.repository`     | cloud-info image repository                          | `enolfc/cloudinfoops`     |
| `cloudInfo.image.tag`            | cloud-info image tag                                 | `0.1.0`                   |
| `cloudInfo.image.pullPolicy`     | cloud-info image pull policy                         | `IfNotPresent`            |
| `cloudInfo.ams.host`             | AMS host                                             | `msg-devel.argo.grnet.gr` |
| `cloudInfo.ams.project`          | cloud-info project name in AMS                       | `egi_cloud_info`          |
| `cloudInfo.ams.token`            | AMS token                                            |                           |
| `cloudInfo.ams.cert`             | AMS host cert (alternative to `cloudInfo.ams.token`) |                           |
| `cloudInfo.ams.key`              | AMS host key                                         |                           |
| `cloudkeeper.schedule`           | CronJob schedule for cloudkeeper                     | `25 */5 * * *`            |
| `cloudkeeper.image.repository`   | cloudkeeper image repository                         | `cloudkeeper/cloudkeeper` |
| `cloudkeeper.image.tag`          | cloudkeeper image tag                                | `2.0.0`                   |
| `cloudkeeper.image.pullPolicy`   | cloudkeeper image pull policy                        | `IfNotPresent`            |
| `cloudkeeper.auth.<vo>`          | AppDB token for accessing the image list             |                           |
| `cloudkeeperOS.service.type`     | Type of service for cloudkeeper-os                   | `ClusterIP`               |
| `cloudkeeperOS.image.repository` | cloudkeeper-os image repository                      | `enolfc/cloudkeeper-os`   |
| `cloudkeeperOS.image.tag`        | cloudkeeper-os image tag                             | `0.1.0`                   |
| `cloudkeeperOS.image.pullPolicy` | cloudkeeper-os image pull policy                     | `IfNotPresent`            |


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
          # authentication for cloud-info
          cloudInfo:
            clientId: YY
            clientSecret: ZZ
            refreshToken: WW
          # authentication for cloudkeeper-os
          cloudkeeper-os:
            clientId: AYY
            clientSecret: BZZ
            refreshToken: CWW
        # optionally specify a protocol for the Keystone V3 federation API
        protocol: openid | oidc (default is openid)
        defaultNetwork: private | public | private_only | public_only (default is public)
        publicNetwork: <name of the public network> (default is UNKNOWN)
```
