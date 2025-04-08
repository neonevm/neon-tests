# Overview

Tests for debug trace iterative

| Test case                                                                        | Description                                                                                                                               | XFailed   |
|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_struct_opcode_tracer | Positive, tracing an iterative transaction using structured opcode tracer.                                                                | NDEV-3595 |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_simple               | Positive, tracing a simple iterative transaction. Check body of response                                                                  |           |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_failed_status        | Positive, tracing a transaction that results in a failed status. Check error in response                                                  |           |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_with_erc20_for_spl   | Positive, tracing an iterative transaction involving ERC-20 tokens for SPL, Check NO error in response                                    |           |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_eip_1559             | Positive, tracing an iterative transaction type EIP-1559 fee mechanism, check body and No error in response                               |           |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_sol_chain            | Positive, tracing an iterative transaction on Sol-chain, check body and No error in response                                              |           |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_block_timestamp      | Positive, verifying block timestamp in an iterative transaction trace. make tx,  get  block by hash and trace tx, check NO error and body |           |
| TestDebugTraceIterativeTransaction::test_trace_scheduled_tx                      | Positive, tracing a simple scheduled transaction, check body and No error in response                                                     |           |
| TestDebugTraceIterativeTransaction::test_trace_success_multiple_scheduled_trx    | Positive, tracing multiple successfully executed scheduled transactions, check trace for each tx, check NO error and body of response     |           |
| TestDebugTraceIterativeTransaction::test_trace_failed_one_scheduled_tx           | Positive, tracing a scheduled transaction that failed, check error exist in response                                                      |           |
| TestDebugTraceIterativeTransaction::test_trace_failed_multiply_scheduled_tx      | Positive, tracing multiple scheduled transactions with failures, check error message  that tx skipped and not supported                   |           |
