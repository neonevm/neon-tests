# Overview

Tests for debug trace transactions callTracer

| Test case                                                                                                     | Description                                                                       | XFailed   |
|---------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|-----------|
| TestDebugTraceTransactionCallTracer::test_callTracer_type_create                                              | Positive, call tracer with type 'create'.                                         |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_type_create2                                             | Positive, call tracer with type 'create2'.                                        |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_type_call                                                | Positive, call tracer with type 'call'.                                           |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_withLog_check                                            | Positive, test to check logs generated during call trace.                         |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_onlyTopCall_check                                        | Positive, test to verify call tracer with only top-level calls.                   | NDEV-2959 |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_static_call             | Positive, static call from one contract to another.                               |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_static_call_with_events | Positive, static call with events in function,                                    |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_call_with_events        | Positive, regular call with events between contracts.                             |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_call                    | Positive, tracing a tx for with contract-to-contract call using 'call' type.      |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_delegate_call           | Positive, tracing a tx for with delegate call between contracts.                  | SLA-119   |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_callcode                | Positive, tracing a tx for with call using 'callcode' between contracts.          |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_with_zero_division                         | Positive, check revert reason in contract call that causes a zero division error. |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert_with_assert     | Positive, check revert reason 'assert'.                                           |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_trivial_revert         | Positive, tracing a tx for with call that triggers a trivial revert.              |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert                 | Positive, tracing a tx for with call that reverts.                                |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert_with_require    | Positive, tracing a tx for with call that reverts with 'require'.                 |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_to_precompiled_contract                             | Positive, tracing a tx for with call ethereum precompiled contract.               |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_without_tracerConfig                                     | Positive, call tracer behavior without explicit tracer config.                    | NDEV-2934 |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_with_event_from_other_one_with_two_events  | Positive, contract call that triggers two events from another contract.           |           |
| TestDebugTraceTransactionCallTracer::test_callTracer_new_contract_and_event_from_constructor                  | Positive, new contract creation and event emission from constructor.              |           |
