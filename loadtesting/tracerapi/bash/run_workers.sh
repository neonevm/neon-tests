#!/bin/bash

trap ctrl_c INT

function ctrl_c() {
    echo "  happened, stoping workers"
    killall screen
    exit 0
}

rpc_host="https://graph.neontest.xyz/neon-rpc"
export NEON_RPC=$rpc_host

read -p "Pass tag to locustfile: " tag
read -p "Pass num running workers: " num


for i in `seq 1 $num`; do
  echo "Running worker $i"
  screen -t w_$i -dm locust -f /home/deploy/neon/tracer-api/loadtesting/tracerapi/locustfile.py -H neon_rpc -T $tag --credentials=/home/deploy/neon/tracer-api/loadtesting/tracerapi/envs.json --worker;
done

echo "To stop running workers press Ctrl+C"
read -r -d '' _ </dev/tty