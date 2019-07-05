#!/bin/sh

if [ "x$TRAVIS_TAG" != "x" ]; then 
    CHARTPRESS_OPT="$CHARTPRESS_OPT --tag $TRAVIS_TAG"
fi
if [ "x$TRAVIS_COMMIT_RANGE" != "x" ]; then
    CHARTPRESS_OPT="$CHARTPRESS_OPT --commit-range $TRAVIS_COMMIT_RANGE";
fi

chartpress $CHARTPRESS_OPT $@
