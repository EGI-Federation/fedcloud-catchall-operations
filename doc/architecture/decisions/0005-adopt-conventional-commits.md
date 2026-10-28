# 5. Adopt Conventional Commits

Date: 2026-10-22

## Status

Proposed

## Context

The history of commits in a repository should aim to describe the changes made to it in terms of functionality and features.
These messages may be interpreted by both human and machine actors, however only the human actors currently have the cognitive ability to interpret free-form commit messages into what those changes actually mean in terms of changes to the application.
What constitutes a new feature or a fix, and thus necessitating the creation of a new release and deployment artifact are open to interpretation and cannot reliably be delegated to a predefined process.

Instead, we desire a repeatable, reliable means to communicate changes to the repository which can be interpreted by a process to determine semantic changes to it: what constitutes a fix to an existing function? What constitutes a new function? What changes should trigger these changes? What changes to the repository do not change the application but instead the developer, test, or release experience?

This problem can be addressed by adopting a shared _vocabulary_ of changes, with clear semantics.
A shared vocabulary of commit messages is a _convention_ adopted by the contributors to a repository, resulting in a shared understanding of what changes are being made to the software.

One of the most widely-used semantics is [Conventional Commits](https://www.conventionalcommits.org) which we propose here to adopt.
Although imperfect, it defines a pragmatic vocabulary which can be parsed by linting tools such as [Commit Lint](https://commitlint.js.org/), and used with automated release tools such as [Semantic Release](https://semantic-release.org/).

## Decision

1. Notify contributors with a badge in the README stating that this repository adopts conventional commits
1. Contributors agree to adopt the Conventional Commits vocabulary
1. Commitlint `pre-commit` should be added to the shared repository hooks
1. Add a commitlint configuration to declare that this repository uses the Conventional Commits vocabulary

## Consequences

1. Commit messages become consistent
1. Changes are semantically interpretable
1. Automated semantic releases become possible
