#!/bin/bash

if [ "x$DEBUG" = "x1" ] ; then
    set -x
fi

EXTRA_OPTS=""

if [ "x$BACKEND_PORT_50051_TCP_ADDR" != "x" ]; then
    EXTRA_OPTS="$EXTRA_OPTS --backend-endpoint=$BACKEND_PORT_50051_TCP_ADDR:$BACKEND_PORT_50051_TCP_PORT"
fi

exec $@ $EXTRA_OPTS
