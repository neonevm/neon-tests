# dApps testing

This project include GHA Workflow for regular testing DApps like Uniswap V2, AAVE and more.
This workflow is triggered by cron every Sunday at 01:00 UTC and run dapps tests, get cost report from
this tests and show this report.

1. Uniswap V2
2. Uniswap 3
3. Saddle finance
4. AAVE
5. Curve and Curve-factory
6. Yearn finance
7. Compound
8. Robonomics


## dApp report

Each DApp generate report in json format and save it in GHA artifacts. Report has structure:

```json
{
    "name": "Saddle finance",
    "actions": [
       {
          "name": "Remove liquidity",
          "usedGas": "123456",
          "gasPrice": "100000000",
          "tx": "0xadasdasdas"
       }
    ]
}
```

In "report" state workflow run clickfile command which print report
