# dApps testing

This project includes GHA Workflow for regular testing DApps like Uniswap V2, AAVE, and more.
This workflow is triggered by cron every Sunday at 01:00 UTC and runs DApp tests, gets a cost report from these tests, and shows this report.

1. Uniswap V2
2. Uniswap 3
3. Saddle finance
4. AAVE
5. Curve and Curve-factory
6. Yearn finance
7. Compound
8. Robonomics


## dApp report

Each DApp generates a report in json format and saves it in GHA artifacts. The report has structure:

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

In the "report" state workflow, run clickfile.py command, which will print the report.
