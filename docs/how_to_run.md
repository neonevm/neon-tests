# How to use

At first, you need to set up a Python 3 virtualenv, and also need to have npm installed and be able to install packages globally on it.

Then you need to install dependencies for the CLI utility:

```bash
pip3 install -r deploy/requirements/click.txt
```

After this, you can use from the project root directory:

```bash
./clickfile.py --help
```

This file contains a lot of utilities to work with this repository, such as:
1. update deps
2. download test contracts
3. run different tests
4. prepare data and stand for run tests


## Install dependencies

Please use clickfile.py to install deps because our web3 has conflicts with solana package, and this problem is resolved in:
```bash
./clickfile.py requirements
```

## Download test contracts

To download test contracts from the Neon EVM repo, you need to use:

```bash
./clickfile.py update-contracts
```

## Run OpenZeppelin tests

To run OpenZeppelin tests just use the next command:
```bash
./clickfile.py run oz --network <your-stand> --jobs 8
```

## Run neon evm tests

To run neon evm tests:
1. set environment variables: 
   SOLANA_URL: by default http://solana:8899
   NEON_CORE_API_URL: by default http://neon_api:8085/api
2. run the next command:
```bash
./clickfile.py run evm --numprocesses 6
```

## Run tests manually

You can run all tests manually if know which framework it uses. For example, economy tests:

```bash
py.test integration/tests/economy/test_economics.py
```

## Run tests on mainnet

To run tests with mark "mainnet"

```bash
./clickfile.py run basic -n mainnet
```

This command collects 73 items and run it on our mainnet. 
Bank accounts envs have to be set up:

```
export BANK_PRIVATE_KEY_MAINNET=
export ETH_BANK_PRIVATE_KEY_MAINNET=
```

To run tests in our ci the following secrets should be added to neon-tests repo:
```
secrets.ETH_BANK_PRIVATE_KEY_MAINNET
secrets.BANK_PRIVATE_KEY_MAINNET
```

Use manual run of Basic tests pipeline with stand option - "mainnet".

An approximate cost of one run is ~200 NEONs and ~0.125 SOL.

## Useful options

- --network - which network uses for run tests (from file envs.json)
- --envs - change file name with networks