import random
import re
import string
import solana

import pytest
from eth_utils import to_text

from .solana_utils import write_transaction_to_holder_account, \
    execute_transaction_steps_from_account_no_chain_id
from .utils.constants import TAG_FINALIZED_STATE
from .utils.contract import make_deployment_transaction, make_contract_call_trx, get_contract_bin
from .utils.ethereum import make_eth_transaction, create_contract_address
from .utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.transaction_checks import check_holder_account_tag, check_transaction_logs_have_text


class TestTransactionStepFromAccountNoChainId:

    def test_simple_transfer_transaction(self, operator_keypair, treasury_pool, evm_loader,
                                         sender_with_tokens, session_user, holder_acc):
        amount = 10
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_before = evm_loader.get_neon_balance(session_user)

        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, amount, chain_id=None)
        write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp = execute_transaction_steps_from_account_no_chain_id(operator_keypair, evm_loader, treasury_pool,
                                                                  holder_acc,
                                                                  [session_user.solana_account_address,
                                                                   session_user.balance_account_address,
                                                                   sender_with_tokens.balance_account_address,
                                                                   sender_with_tokens.solana_account_address], 0)

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_after = evm_loader.get_neon_balance(session_user)

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp.value.transaction.transaction.signatures[0], "exit_status=0x11")
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after

    def test_deploy_contract(self, operator_keypair, holder_acc, treasury_pool, evm_loader, sender_with_tokens,
                             neon_api_client):
        contract_filename = "hello_world"
        contract = create_contract_address(sender_with_tokens, evm_loader)

        signed_tx = make_deployment_transaction(sender_with_tokens, contract_filename, chain_id=None)
        write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        contract_code = get_contract_bin(contract_filename)

        steps_count = neon_api_client.get_steps_count(sender_with_tokens, None, contract_code)
        resp = execute_transaction_steps_from_account_no_chain_id(operator_keypair, evm_loader, treasury_pool,
                                                                  holder_acc,
                                                                  [contract.solana_address,
                                                                   contract.balance_account_address,
                                                                   sender_with_tokens.balance_account_address,
                                                                   sender_with_tokens.solana_account_address],
                                                                  steps_count)
        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp.value.transaction.transaction.signatures[0], "exit_status=0x12")

    def test_call_contract_function_with_neon_transfer(self, operator_keypair, treasury_pool,
                                                       sender_with_tokens, string_setter_contract, holder_acc,
                                                       evm_loader, neon_api_client):
        transfer_amount = random.randint(1, 1000)

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens)
        contract_balance_before = evm_loader.get_neon_balance(string_setter_contract.eth_address)

        text = ''.join(random.choice(string.ascii_letters) for _ in range(10))

        signed_tx = make_contract_call_trx(sender_with_tokens, string_setter_contract, "set(string)", [text],
                                           value=transfer_amount, chain_id=None)
        write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        resp = execute_transaction_steps_from_account_no_chain_id(operator_keypair, evm_loader, treasury_pool,
                                                                  holder_acc,
                                                                  [string_setter_contract.solana_address,
                                                                   string_setter_contract.balance_account_address,
                                                                   sender_with_tokens.balance_account_address,
                                                                   sender_with_tokens.solana_account_address]
                                                                  )

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp.value.transaction.transaction.signatures[0], "exit_status=0x11")

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens)
        contract_balance_after = evm_loader.get_neon_balance(string_setter_contract.eth_address)
        assert sender_balance_before - transfer_amount == sender_balance_after
        assert contract_balance_before + transfer_amount == contract_balance_after

        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

    def test_transaction_with_access_list(self, operator_keypair, treasury_pool,
                                          sender_with_tokens, calculator_contract, calculator_caller_contract,
                                          holder_acc, evm_loader):
        access_list = (
            {
                "address": '0x' + calculator_contract.eth_address.hex(),
                "storageKeys": (
                    "0x0000000000000000000000000000000000000000000000000000000000000000",
                )
            },
        )
        signed_tx = make_contract_call_trx(sender_with_tokens, calculator_caller_contract, "callCalculator()", [],
                                           chain_id=None, access_list=access_list)
        write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        error = re.escape("assertion failed: trx.chain_id().is_none()")
        with pytest.raises(solana.rpc.core.RPCException, match=error):
            execute_transaction_steps_from_account_no_chain_id(operator_keypair, evm_loader, treasury_pool,
                                                               holder_acc,
                                                               [calculator_contract.solana_address,
                                                                calculator_caller_contract.solana_address,
                                                                sender_with_tokens.balance_account_address,
                                                                sender_with_tokens.solana_account_address]
                                                               )
