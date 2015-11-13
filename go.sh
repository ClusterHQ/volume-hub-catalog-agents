#!/bin/sh
if [ "$TARGET" = "control-service" ]; then
    sudo docker rm -f volume-hub-agent-dataset || false
    sudo docker pull clusterhq/catalog-agents-dataset
    sudo -E docker run -d --restart=always \
        -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
        -v /etc/flocker:/etc/flocker \
        -v /var/run/docker.sock:/var/run/docker.sock \
        --name volume-hub-agent-dataset \
        clusterhq/catalog-agents-dataset
elif [ "$TARGET" = "agent-node" ]; then
    sudo docker rm -f volume-hub-agent-docker || false
    sudo docker pull clusterhq/catalog-agents-docker
    sudo -E docker run -d --restart=always \
        -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
        -v /etc/flocker:/etc/flocker \
        -v /var/run/docker.sock:/var/run/docker.sock \
        --name volume-hub-agent-docker \
        clusterhq/catalog-agents-docker
fi
# This runs on all of them
sudo docker rm -f volume-hub-agent-log || false
sudo docker pull clusterhq/catalog-agents-log
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --name volume-hub-agent-log \
    clusterhq/catalog-agents-log
sudo docker rm -f volume-hub-agent-node || false
sudo docker pull clusterhq/catalog-agents-node
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --name volume-hub-agent-node \
    clusterhq/catalog-agents-node
