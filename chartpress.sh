#!/bin/sh

set -e

# let's assume that we need to login if params are there
if [ -n "$@" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

if [ "x$TRAVIS_TAG" != "x" ]; then 
    CHARTPRESS_OPT="$CHARTPRESS_OPT --tag $TRAVIS_TAG"
fi
if [ "x$TRAVIS_COMMIT_RANGE" != "x" ]; then
    CHARTPRESS_OPT="$CHARTPRESS_OPT --commit-range $TRAVIS_COMMIT_RANGE";
fi

chartpress $CHARTPRESS_OPT $@
