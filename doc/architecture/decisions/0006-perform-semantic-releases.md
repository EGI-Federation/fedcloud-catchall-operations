# 6. Perform Semantic Releases

Date: 2026-10-22

## Status

Proposed

## Context

Only changes to the application should be deployed.

Changes to the application are communicated via the [Semantic Versioning](https://semver.org/) specification (SemVer).
The SemVer spec defines what changes to the software's internal and external APIs (interpreted in the context of the relevant software itself), and defines a grammar for communicating those changes.

This specification allows predefined processes to compute the next _Semantic Version_ of a project's release.

When combined with a shared convention in communicating changes with a consistent vocabulary, such as [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), the SemVer specification can be used to compute this next version without the need for human cognition, relying on the convention's vocabulary of changes, and the list of changes between two subsequent releases.

A "release" here refers explicitly to:

* Definition of "release branches": pre-releases can be declared to be performed on specific preview branches (_e.g._ `feat-xyz`, `pre-xyz`) , while "releases" are declared to be performed on the "main" branch (_i.e._ `main`). By default there is only one default branch, the main branch.
* A git tag respecting the SemVer specification added to the branch to declare where the release occurred
* A [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

## Decision

1. Perform Semantic Releases using relevant tooling in the CI/CD pipeline
2. Use GitHub Releases to publish release artifacts
3. Apply tags to release artifacts with Semantic Versions compute via release process, using the outcome of the process.

## Consequences

We address [#661](https://github.com/EGI-Federation/fedcloud-catchall-operations/issues/661).

The CI/CD pipeline is affected - we are able to decouple delivery from deployment.

Delivery occurs when it is determined that new artifacts are required -- the condition is a **new release**.
When no new releases are needed, only CI is performed: internal validation, linting, unit tests.
When a new release is computed, full tests are invoked, a new artifact is built and _delivered_ (_i.e._ pushed to artifact registries, _e.g._ new container image, new python library version _etc._)

Deployment is then optionally invoked based on the trigger that a new semantic version is present.
Currently, it is invoked via dispatch without release criteria.

The overall consequence is deployment only on changes to the actual application, and suppression of deploy pipelines and events on internal maintenance chores, _etc_.
