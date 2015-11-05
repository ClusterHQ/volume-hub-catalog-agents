Herein are the ClusterHQ Volume Hub Catalog Agents.

Install them on all the nodes in your Flocker cluster and they will push data from your cluster (volumes, containers, logs) into the Flocker volume hub.

TODO: The UFT installer will automatically install these for you if you specify an appropriate key in your `cluster.yml`.

# Install

If you already have a Flocker cluster, you can follow these instructions to install the catalog agents manually.

Before installing, register for a volume hub account at [https://volumehub.io](https://volumehub.io).

Then click "create a cluster" and then copy your secret token into the following command, which you must run on each of your Flocker cluster nodes, replacing ABC with your token below:

```
$ curl -ssL https://get.volumehub.io |TOKEN=ABC sh
```
