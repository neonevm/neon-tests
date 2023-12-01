# Overview

Tests for estimate gas

| Test case                                                                 | Description                                                        | XFailed |
|---------------------------------------------------------------------------|--------------------------------------------------------------------|---------|
| TestRpcEstimateGas::test_eth_estimate_gas                                 | Get estimate gas for contract                                      |         |
| TestRpcEstimateGas::test_eth_estimate_gas_negative                        | Get estimate gas without params                                    |         |
| TestRpcEstimateGas::test_eth_estimate_gas_with_big_int                    | Get estimate gas for a big contract                                |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_send_neon                       | Get estimate gas for send neon transfer operation                  |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_erc20                           | Get estimate gas for erc20 transfer operation                      |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_spl                             | Get estimate gas for spl transfer operation                        |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_get_value              | Get estimate gas for getting value from the contract               |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_set_value              | Get estimate gas for setting value in the contract                 |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_calls_another_contract | Get estimate gas for calling function in one contract from another |         |
