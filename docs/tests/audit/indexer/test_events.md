# Overview

Tests for neon logs events

| Test case                                             | Description                   | XFailed |
|-------------------------------------------------------|-------------------------------|---------|
| TestEvents::test_events_for_trx_with_transfer         | Transaction with transfer     |         |
| TestEvents::test_field_values_for_trx_with_transfer   | Check transaction fields      |         |
| TestEvents::test_events_for_trx_with_logs             | Check transaction with logs   |         |
| TestEvents::test_events_for_trx_with_nested_call      | Check nested calls            |         |
| TestEvents::test_contract_iterative_tx                | Check iterative calls         |         |
| TestEvents::test_event_enter_call_code                | Check CodeCall                |         | 
| TestEvents::test_event_enter_static_call              | Check StaticCall              |         | 
| TestEvents::test_event_enter_delegate_call            | Check DelegateCall            |         | 
| TestEvents::test_event_enter_create_2                 | Check Create2 call            |         | 
| TestEvents::test_event_exit_return                    | Check ExitReturn              |         | 
| TestEvents::test_event_exit_self_destruct             | Check SelfDestruct            |         | 
| TestEvents::test_event_exit_send_all                  | Check SendAll                 |         | 
| TestEvents::test_event_cancel                         | Check Cancel                  |         | 