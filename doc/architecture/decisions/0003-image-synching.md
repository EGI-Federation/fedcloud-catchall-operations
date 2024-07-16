# 3. Image synching

Date: 2024-07-12

## Status

Accepted

## Context

EGI provides an image repository (AppDB) for users to share VM images and VOs to
add them to a list of images to be available at the sites supporting the VO.
This has been managed with the installation and configuration of specific tools at
site-level although the uploading of images is for most sites a user-level operation
that does not need any special privileges.

The main software product for this is
[cloudkeeper](https://github.com/the-cloudkeeper-project/cloudkeeper), which
takes care of analysing the list of images, downloading them locally and then
uploading them to the configured Glance endpoint. cloudkeeper has a pluggable
architecture with a server component (backend) managing the connection with the
cloud site and a fronted component managing the lists. While this allows for
supporting multiple cloud providers, at the moment this complexity brings no
clear added value. [atrope](https://github.com/IFCA-Advanced-Computing/atrope)
is a simpler alternative implementation that focuses on OpenStack.

Both Cloudkeeper and atrope do not have any recent development.

## Decision

Operate a central image synching that takes care of making the images available
at the sites for all the EGI VOs. Use atrope as it's easier to develop and
adjust to our needs.

Make the synchronisation optional for sites so we can roll the feature gradually
or avoid it completely for those sites where image uploading is not available
for users.

## Consequences

With this change in place:

- sites won't need to run cloudkeeper, the management of VM images becomes
  responsibility of the fedcloud control panel
- we can get ready for the new implementation of AppDB faster as there is only
  one place to adjust
- we introduce a single point of failure for the image synchronisation which may
  be problematic in the future
