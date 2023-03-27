# Overview

A main repository for all types of tests in NEON for proxy and evm.

## How to use

At first you need to setup a Python 3 virtualenv, and also need to have npm installed, and be able to install packages globally on it. You'll also need to install solc.

Then you need install a main dependency for CLI utility:

```bash
pip3 install click==8.0.3
```

After this you can use from project root directory:

```bash
./clickfile.py --help
```

This file contains a lot of utilities to work with this repository such as:
1. update deps
2. download test contracts
3. run different tests
3. prepare data and stand for run tests


## Install dependencies

Please use clickfile.py to install deps because our web3 has conflicts with solana package and this problem resolved in:
```bash
./clickfile.py requirements
```

## Download test contracts

To download test contracts from the neon-evm repo you need to use:

```bash
./clickfile.py contracts
```

## Run OpenZeppelin tests

To run OpenZeppelin tests just use next command:
```bash
./clickfile.py run oz --network <your-stand> --jobs 8
```


## Run tests manual

You can run all tests manual uif know which framework it uses. For example economy tests:

```bash
py.test integration/tests/economy/test_economics.py
```

## Useful options

- --network - which network uses for run tests (from file envs.json)
- --envs - change file name with networks

## Structure

For our Proxy and EVM we need to use a lot of frameworks, languages, contracts and scenarios. For this I propose this
structure:

1. Top level we split for different types of tests by : loadtesting, integration, compatibility tests.
    - utils - some python utils which can help write integration, loadtesting and another python tests
    - deploy - directory with docker files, configs and files for deploy
    - allure - directory with allure configs
    - envs.yml - stand configurations
    - clickfile.py - file with CLI interface with different tasks to run all tests and prepare it.
2. Compatibility - we need to test our infrastructure for compatibility with different framework on different languages
    - openzeppelin - directory with our openzeppelin fork (submodule). To run this tests manual use clickfile.py
      openzeppelin
    - contracts - a directory for opensource contracts in solidity. We will deploy and run tests for it (if exists)
    - frameworks - a directory for frameworks splitted by language. All this frameworks need to run integrated tests (if
      exist)
      or realize one basic scenario (like: create several accounts, get evm version, get blocks, make several
      transactions, deploy one contract). Each framework and language has private structure and we don't need to change
      it and use good practices for each language.
3. Loadtesting - future tests for load testing
4. Integration - integration tests for base functionalitiy; operator economy and so


## Useful tips

To get neon operator reward address from solana private, we need to use:
```python
import os
import json
from solana.account import Account
from common_neon.address import EthereumAddress

keys = []
for f in os.listdir("operator-keypairs"):
    with open(f"operator-keypairs/{f}", "r") as key:
        a = Account(json.load(key)[:32])
        keys.append(str(EthereumAddress.from_private_key(a.secret_key())))
```


## DApps testing
This project include GHA Workflow for regular testing DApps like Uniswap V2, AAVE and more.
This workflow is triggered by cron every Sunday at 01:00 UTC and run dapps tests, get cost report from
this tests and show this report.

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
