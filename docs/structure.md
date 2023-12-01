# Structure

For our Proxy and EVM, we need to use a lot of frameworks, languages, contracts, and scenarios. For this, I propose this
structure:

1. Top level split to different types of tests by load testing, integration, and compatibility tests.
    - utils - some Python utils which can help write integration, load testing, and other Python tests
    - deploy - directory with docker files, configs, and files for deploy
    - allure - directory with allure configs
    - envs.yml - stand configurations
    - clickfile.py - file with CLI interface with different tasks to run all tests and prepare it.
2. Compatibility - we need to test our infrastructure for compatibility with different frameworks in different languages
    - openzeppelin - directory with our openzeppelin fork (submodule). To run this tests manual use clickfile.py
      openzeppelin
    - contracts - a directory for open-source contracts in solidity. We will deploy and run tests for it (if exists)
    - frameworks - a directory for frameworks split by language. All these frameworks need to run integrated tests (if
      exist)
      or realize one basic scenario, like creating several accounts, getting EVM version, get blocks, making several transactions, or deploying one contract. Each framework and language has a  private structure, and we don’t need to change it and use good practices for each language.
3. Loadtesting - future tests for load testing
4. Integration - integration tests for base functionality; Operator economy and so on.