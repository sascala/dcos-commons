#!/bin/bash
for INDEX in 0 1; do
    HOST="node-$INDEX-server.$SERVICE_NAME.mesos"
    echo "Checking availability of Mesos DNS for $HOST..."
    while nslookup $HOST | grep "server can't find" > /dev/null; do
        echo "Waiting for $HOST to resolve..."
        sleep 5
    done
done
