#!/bin/sh
docker build -t clusterhq/catalog-agents-core catalog_client
docker build -t clusterhq/catalog-agents-docker catalog_client/docker
docker build -t clusterhq/catalog-agents-dataset catalog_client/dataset
docker build -t clusterhq/catalog-agents-log catalog_client/log
docker build -t clusterhq/catalog-agents-node catalog_client/node
