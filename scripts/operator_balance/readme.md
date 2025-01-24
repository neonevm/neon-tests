# Tools for Operator balance monitoring
* [operator_balance_daily_report.py](./operator_balance_daily_report.py) is used to generate a csv report with Operator balance broken down into days
* [operator_balance_to_prometheus.py](./operator_balance_to_prometheus.py) is used to collect and push Operator balance metrics to Prometheus


## Pre-requisites
1. Install Docker Desktop
   See the guide for [Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Windows](https://docs.docker.com/desktop/setup/install/windows-install/) or [Linux](https://docs.docker.com/desktop/setup/install/linux/)

2. Place a json file with operator names and Solana keys __in the current directory__ with the following structure:
   ```json5
   // operators.json
   [
     {
       "name": "Operator A",
       "accounts": [
         "...",
         "..."
       ]
     },
     {
       "name": "Operator B",
       "accounts": [
         "...",
         "..."
       ]
     }
   ]
   ```
3. Pull and spin neon_tests container, sharing the current directory with it
   ```shell
   docker pull neonlabsorg/neon_tests:latest && \
   docker run -d --name neon_tests -v "./:/scripts/operator_balance" neonlabsorg/neon_tests:latest tail -f /dev/null
   ```
4. Connect to VPN
   See the guide [here](https://www.notion.so/neonfoundation/Setting-Up-Xray-VPN-Clients-c3208c94d6894726aaac8902d2a02f04)

### Generate operator balance daily report
1. Replace ... placeholders with your values and run the script in the container
    ```shell
    docker exec -it neon_tests bash -c 'python3 -m scripts.operator_balance.operator_balance_daily_report \
        --operators "/scripts/operator_balance/operators.json" \
        --report_dir "/scripts/operator_balance" \
        --from_slot ... \
        --to_slot ... \
        --indexer_pg_host ... \
        --indexer_pg_db ... \
        --indexer_pg_user ... \
        --indexer_pg_password ...'
    ```
2. View the report
It will be placed in your current directory and named `operator_daily_report_<timestamp>.csv`

### Collect operator balance data and push it to Prometheus
Replace ... placeholders with your values and run the script in the container
```shell
docker exec -it neon_tests bash -c 'python -m scripts.operator_balance.operator_balance_to_prometheus \
   --operators "/scripts/operator_balance/operators.json" \
   --prometheus_url ... \
   --push_gateway_url ... \
   --indexer_pg_host ... \
   --indexer_pg_db ... \
   --indexer_pg_user ... \
   --indexer_pg_password ...'
```
