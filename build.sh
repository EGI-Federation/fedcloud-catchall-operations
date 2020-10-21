#!/usr/bin/env bash

set -euo pipefail

TRAVIS_TAG=${TRAVIS_TAG:-""}

docker build -t egifedcloud/ops-cloud-info:$TRAVIS_TAG -t egifedcloud/ops-cloud-info:latest cloud-info
