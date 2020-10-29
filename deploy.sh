#!/usr/bin/env bash

set -euo pipefail

# let's assume that we need to login if params are there
if [ -n "$DOCKER_PASSWORD" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

docker push egifedcloud/ops-cloud-info:latest
if [ -n "$TRAVIS_TAG" ]; then
	docker push "egifedcloud/ops-cloud-info:$TRAVIS_TAG"
fi
