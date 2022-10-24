#!/bin/bash

rpc_host="https://graph.neontest.xyz/neon-rpc"

export NEON_RPC=$rpc_host

read -p "Pass tag to locustfile: " tag

locust -f /home/deploy/neon/tracer-api/loadtesting/tracerapi/locustfile.py -H neon_rpc -T $tag --credentials=/home/deploy/neon/tracer-api/loadtesting/tracerapi/envs.json --master