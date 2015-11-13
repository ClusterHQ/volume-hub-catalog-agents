#!/bin/sh
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    clusterhq/catalog-agents-docker
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    clusterhq/catalog-agents-dataset
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    clusterhq/catalog-agents-node
sudo -E docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    clusterhq/catalog-agents-log
