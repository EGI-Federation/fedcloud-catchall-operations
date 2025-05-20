# 2. JSON rendering

Date: 2024-05-24

## Status

Accepted

## Context

The information published by cloud-info-provider has used GLUE2.1 LDIF
rendering as this was initially used for publication into a LDAP-based BDII.
As we moved to the AppDB IS, BDII is no longer needed, still as the AppDB IS
implementation was created with BDII in mind, it was ready to parse LDIF files
and it was easier/faster to keep producing information in that format.

Now for the redesign of the system, LDIF is no longer a requirement and formats
easier to handle and queried can be used. Besides
[LDIF](https://github.com/OGF-GLUE/LDAP), GLUE2.1 has [XML](https://github.com/OGF-GLUE/XSD),
[SQL](https://github.com/OGF-GLUE/SQL), and [JSON](https://github.com/OGF-GLUE/JSON).

## Decision

Start producing information using the GLUE JSON rendering, getting ready for
its consumption by new tools to be developed that will eventually replace the
AppDB IS. Publish this information into a S3 bucket with a directory per
available site. For uploading the JSON objects use [rclone](https://rclone.org/)
as this is a generic tool that can work with the potential S3 storage providers
that we will use (CloudFlare/MinIO/Swift)

Keep publishing the LDIF rendering through the AMS for the AppDB IS.

## Consequences

No changes for the AppDB IS as we keep publishing the LDIF rendering, but this
will enable the development of a replacement using a new source of information.
