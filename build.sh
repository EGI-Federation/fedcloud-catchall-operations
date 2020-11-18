#!/usr/bin/env bash

set -euo pipefail

set -x

docker build -t egifedcloud/ops-cloud-info:latest $EXTRA_TAG cloud-info

if [ -n "$TRAVIS_TAG" ]; then
    docker build -t "egifedcloud/ops-cloud-info:$TRAVIS_TAG" cloud-info
fi
