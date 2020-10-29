#!/usr/bin/env bash

set -euo pipefail

EXTRA_TAG=""
if [ -n "$TRAVIS_TAG" ]; then
    EXTRA_TAG="-t egifedcloud/ops-cloud-info:$TRAVIS_TAG"
fi

docker build -t egifedcloud/ops-cloud-info:latest "$EXTRA_TAG" cloud-info
