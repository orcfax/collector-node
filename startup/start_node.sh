#! /usr/bin/bash

cardano-node run \
 --config /home/orcfax/cardano-node/mainnet-config/config.json \
 --topology /home/orcfax/cardano-node/mainnet-config/topology.json \
 --socket-path /home/orcfax/cardano-node/node.socket \
 --database-path /home/orcfax/cardano-node/mainnet-db \
 --host-addr 0.0.0.0
