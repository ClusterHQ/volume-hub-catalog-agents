#!/bin/sh
if [ "$RUN_FLOCKER_AGENT_HERE" = "1" ]; then
    sudo docker rm -f volume-hub-agent-dataset || false
    sudo docker pull clusterhq/catalog-agents-dataset
    sudo -E docker run -d --restart=always \
        -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
        -e CATALOG_FIREHOSE_HOSTNAME \
        -e FLOCKER_CONFIGURATION_PATH=/host/etc/flocker \
        -v /:/host \
        --name volume-hub-agent-dataset \
        clusterhq/catalog-agents-dataset
fi

if [ "$TARGET" = "agent-node" ]; then
    sudo docker rm -f volume-hub-agent-docker || false
    sudo docker pull clusterhq/catalog-agents-docker
    sudo -E docker run -d --restart=always \
        -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
        -e CATALOG_FIREHOSE_HOSTNAME \
        -e FLOCKER_CONFIGURATION_PATH=/host/etc/flocker \
        -v /:/host \
        --name volume-hub-agent-docker \
        clusterhq/catalog-agents-docker
fi

# This runs on all of them
sudo docker rm -f volume-hub-agent-log || false
sudo docker pull clusterhq/catalog-agents-log
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -e CATALOG_FIREHOSE_HOSTNAME \
    -e FLOCKER_CONFIGURATION_PATH=/host/etc/flocker \
    -v /:/host \
    --name volume-hub-agent-log \
    clusterhq/catalog-agents-log

sudo docker rm -f volume-hub-agent-node || false
sudo docker pull clusterhq/catalog-agents-node
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -e CATALOG_FIREHOSE_HOSTNAME \
    -e FLOCKER_CONFIGURATION_PATH=/host/etc/flocker \
    -v /:/host \
    --name volume-hub-agent-node \
    clusterhq/catalog-agents-node
