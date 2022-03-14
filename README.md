# Overview

A main repository for all types of tests in NEON for proxy and evm.

## How to use

At first you need install a main dependency for CLI utility:

```bash
pip3 install click==8.0.3
```

After this you can use from project root directory:

```bash
./clickfile.py --help
```

This file contains a lot of utilities to work with this repository such as:
1. update deps
2. run different tests
3. prepare data and stand for run tests


##Install dependencies

Please use clickfile.py to install deps because our web3 has conflicts with solana package and this problem resolved in:
```bash
./clickfile.py requirements
```


##Run tests manual

You can run all tests manual uif know which framework it uses. For example economy tests:

```bash
py.test integration/tests/economy/test_economics.py
```

##Useful options

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
