# How to use

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
4. prepare data and stand for run tests


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
