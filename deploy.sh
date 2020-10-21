#!/usr/bin/env bash

set -euo pipefail

TRAVIS_TAG=${TRAVIS_TAG:-""}

# let's assume that we need to login if params are there
if [ -n "$DOCKER_PASSWORD" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

docker push egifedcloud/ops-cloud-info:$TRAVIS_TAG egifedcloud/ops-cloud-info:latest
