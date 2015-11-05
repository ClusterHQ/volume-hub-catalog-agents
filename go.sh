#!/bin/sh
docker run -d --restart=always \
    -e CATALOG_FIREHOSE_SECRET="$TOKEN" \
    -v /etc/flocker:/etc/flocker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    clusterhq/catalog-agent-docker
