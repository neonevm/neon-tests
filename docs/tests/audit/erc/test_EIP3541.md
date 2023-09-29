# Overview

Test for EIP-3541: Reject new contract code starting with the 0xEF byte

# Tests list

| Test case                                                                        | Description                                               | XFailed |
|----------------------------------------------------------------------------------|-----------------------------------------------------------|---------|
| TestRejectingContractsStartingWith0xEF::test_sent_incorrect_calldata_via_trx     | Reject transaction with bad call data                     |         |
| TestRejectingContractsStartingWith0xEF::test_sent_correct_calldata_via_trx       | Check good path                                           |         |
| TestRejectingContractsStartingWith0xEF::test_sent_correct_calldata_via_create2   | Check good path via create2 instruction                   |         |
| TestRejectingContractsStartingWith0xEF::test_sent_incorrect_calldata_via_create2 | Check error via create2 instruction with invalid calldata |         |
