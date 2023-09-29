# Structure

For our Proxy and EVM we need to use a lot of frameworks, languages, contracts and scenarios. For this I propose this
structure:

1. Top level we split for different types of tests by : loadtesting, integration, compatibility tests.
    - utils - some python utils which can help write integration, loadtesting and another python tests
    - deploy - directory with docker files, configs and files for deploy
    - allure - directory with allure configs
    - envs.json - stand configurations
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
