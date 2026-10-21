# 4. Use Pre-Commit Hooks

Date: 2026-10-21

## Status

Proposed

## Context

Pre-commit hooks run predetermined checks against commits to the repository, which are used to ensure a level of consistency and quality of the codebase, as well as protect against malicious or malformed contribution.
Examples of these are accidentally adding secrets to the git history, or committing changes which do not respect an agreed-upon convention.

Pre-commit hooks work best when all contributors use the same set of hooks.
The pre-commit framework supports the use of a single configuration file `.pre-commit-config.yaml` which declares the list of hooks and their configuration adopted in this repository.

While the pre-commit framework was originally written in Python, we use the more efficient and feature-rich implementation in Rust: `prek`.

Pre-commit hooks should be added to the repository by all contributors:

```
prek install
prek install
Installed Git hook at `.git/hooks/pre-commit`
prek install --hook-type=commit-msg
Installed Git hook at `.git/hooks/commit-msg`
```

Where pre-commit hooks were already installed, the `--overwrite` flag should be passed.

This ensures that hooks are enabled for the commit stage, as well as the commit message linting stage, enforcing quality on both codebase as well as commit history.

## Decision

Adopt the `pre-commit` framework and use `prek` to manage the hooks.
Adopt documentation that helps contributors to install the hooks before they continue committing to the repository.
To make the developer experience more consistent, we use `mise` to provide the relevant tools.
Use of Mise is optional.

## Consequences

* existing contributors should be required to install the pre-commit hooks into their development environment
* We provide the `pre-commit` configuration in this repository in `.pre-commit-config.yaml`
* We provide the developer environment definition with `mise.toml`
* If developers choose to use `mise` to manage the development environment, they are guaranteed a working setup, else they can use alternatives to install the git hooks.
* If pre-commit hooks are not run, commit messages may not be linted, defects and secrets may enter the commit history, and we remain at the status-quo.
