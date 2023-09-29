# Overview for tests in basic directory

Is a root directory for basic blockchain operations, erc/eip verification etc.


## Tests by files

All tests splitted by categories and files:

1. erc - directory for all tests connected with ERC/EIP
2. evm - directory for tests where checks evm specific functionality
3. oracles - checks for oracles (pyth, chainlink)


Files in root directory:

1. [test_rpc_calls.py](docs/tests/audit/test_rpc_calls.md) - all tests to check availability for different rpc calls
2. [test_nonce.py](docs/tests/audit/test_nonce.md) - tests to verify mempool and work with nonce
3. [test_contract_reverting.py](docs/tests/audit/test_contract_reverting.md) - tests to check revert in contracts
4. [test_deposit.py](docs/tests/audit/test_deposit.md) - tests for deposit and withdraw operations (neon <-> solana tokens transfer)
5. [test_event_logs.py](docs/tests/audit/test_event_logs.md) - tests for events in contracts
6. [test_failed_transactions.py](docs/tests/audit/test_failed_transactions.md) - check failed transactions
7. [test_transfers.py](docs/tests/audit/test_transfers.md) - check transfer operations with neon/spl/erc tokens
8. [test_trx_rlp_decoding.py](docs/tests/audit/test_trx_rlp_decoding.md) - verify bad sign or bad transaction body
9. [test_wneon.py](docs/tests/audit/test_wneon.md) - tests for wrap/unwrap neon token