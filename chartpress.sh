#!/bin/bash

set -euo pipefail

CHARTPRESS_OPT="$@"
TRAVIS_TAG=${TRAVIS_TAG:-""}
TRAVIS_COMMIT_RANGE=${TRAVIS_COMMIT_RANGE:-""}

# let's assume that we need to login if params are there
if [ -n "$CHARTPRESS_OPT" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

if [ -n "$TRAVIS_TAG" ]; then
    CHARTPRESS_OPT="$CHARTPRESS_OPT --tag $TRAVIS_TAG"
fi
if [ -n "$TRAVIS_COMMIT_RANGE" ]; then
    CHARTPRESS_OPT="$CHARTPRESS_OPT --commit-range $TRAVIS_COMMIT_RANGE";
fi

chartpress $CHARTPRESS_OPT
