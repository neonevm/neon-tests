import json
import os
import random
import time
from decimal import Decimal

import allure
import pytest
import rlp
from eth_account.signers.local import LocalAccount
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair as SolanaAccount, Keypair
from solders.pubkey import Pubkey
from solana.rpc.types import Commitment

from web3.contract import Contract
from web3.exceptions import Web3RPCError

from utils import helpers
from utils.accounts import EthAccounts
from utils.consts import LAMPORT_PER_SOL, Time, COUNTER_ID
from utils.erc20 import ERC20
from utils.helpers import wait_condition, gen_hash_of_block, decode_function_signature, serialize_instruction
from utils.neon_user import NeonUser
from utils.operator import Operator
from utils.scheduled_trx import CreateTreeAccMultipleData, ScheduledTrxEstimateRequest, ScheduledTransaction
from utils.solana_client import SolanaClient
from utils.solana_interoperability_helper import prepare_transfer_spl_data
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client, Web3Client, BASE_MAX_PRIORITY_FEE
from .const import INSUFFICIENT_FUNDS_ERROR, GAS_LIMIT_ERROR, BIG_STRING
from .steps import (
    assert_profit,
    get_gas_used_percent,
    check_alt_off,
    check_alt_on,
    wait_until_alt_deleted,
)

from ..basic.helpers.chains import make_nonce_the_biggest_for_chain
from ..basic.helpers.rpc_checks import check_trx_is_success


@pytest.fixture(scope="class", autouse=True)
def heat_stand(web3_client, faucet):
    """After redeploy stand, first 10-20 requests spend more sols than expected."""
    if "CI" not in os.environ:
        return
    acc = web3_client.eth.account.create()
    faucet.request_neon(acc.address, 100)
    for _ in range(20):
        web3_client.send_neon(acc, web3_client.eth.account.create(), 1)


@allure.story("Operator economy")
class TestEconomics:
    @pytest.mark.only_stands
    def test_account_creation(self, client_and_price, operator):
        """Verify account creation spend SOL"""
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(w3_client)
        acc = w3_client.eth.account.create()
        assert w3_client.get_balance(acc.address) == Decimal(0)
        sol_balance_after = operator.get_solana_balance()
        neon_balance_after = operator.get_token_balance(w3_client)
        assert neon_balance_after == neon_balance_before
        assert sol_balance_after == sol_balance_before

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_send_neon_to_non_existent_account(
        self,
        account_with_all_tokens: LocalAccount,
        client_and_price: tuple[Web3Client, float],
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Verify how many cost transfer of native chain token to new user"""
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        transfer_value = 500000
        acc2 = w3_client.create_account()
        receipt = w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value, tx_type=tx_type)
        assert w3_client.get_balance(acc2) == transfer_value

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after, "Operator SOL balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)
        get_gas_used_percent(w3_client, receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_send_tokens_to_exist_account(
        self,
        account_with_all_tokens: LocalAccount,
        client_and_price: tuple[Web3Client, float],
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Verify how many cost token send to use who was already initialized"""
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        transfer_value = 5000
        w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value // 2, tx_type=tx_type)

        assert w3_client.get_balance(acc2) == transfer_value // 2

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        receipt = w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value // 2, tx_type=tx_type)

        assert w3_client.get_balance(acc2) == transfer_value

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after
        get_gas_used_percent(w3_client, receipt)

        assert sol_balance_before > sol_balance_after, "Operator balance after send tx doesn't changed"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)

    @pytest.mark.skip(reason="Trxs without chain_id doesn't have profit with current CI stand configuration")
    def test_send_neon_token_without_chain_id(
        self, account_with_all_tokens, web3_client, sol_price, operator, neon_price, accounts
    ):
        # for neon token transactions without chain_id NeonEVM
        # checks eip1820
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        instruction_tx = web3_client.make_raw_tx(
            account_with_all_tokens.address, accounts[1].address, 100, estimate_gas=True, chain_id=None
        )
        web3_client.send_transaction(account_with_all_tokens, instruction_tx)
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        sol_diff = sol_balance_before - sol_balance_after

        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, neon_price, web3_client.native_token_name)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_send_when_not_enough_tokens_to_gas(
        self,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        operator: Operator,
        tx_type: TransactionType,
    ):
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()

        assert w3_client.get_balance(acc2) == 0
        transfer_amount = 5000
        w3_client.send_tokens(account_with_all_tokens, acc2, transfer_amount, tx_type=tx_type)
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        acc3 = w3_client.create_account()

        with pytest.raises(Web3RPCError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.send_tokens(acc2, acc3, transfer_amount, tx_type=tx_type)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_before == token_balance_after

    def test_erc20_for_spl_transfer(self, erc20_wrapper, client_and_price, sol_price, operator, accounts):
        sender_account = accounts[0]
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        assert erc20_wrapper.contract.functions.balanceOf(sender_account.address).call() == 0
        transfer_tx = erc20_wrapper.transfer(erc20_wrapper.owner, sender_account, 25)

        assert erc20_wrapper.contract.functions.balanceOf(sender_account.address).call() == 25
        wait_condition(lambda: sol_balance_before > operator.get_solana_balance())
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)

        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)

        get_gas_used_percent(w3_client, transfer_tx)

    def test_erc721_mint(self, erc721, client_and_price, account_with_all_tokens, sol_price, operator):
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        seed = w3_client.text_to_bytes32(gen_hash_of_block(8))

        erc721.mint(seed, account_with_all_tokens.address, "uri")

        wait_condition(lambda: sol_balance_before > operator.get_solana_balance())
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_withdraw_neon_unexisting_ata(
        self,
        neon_price: float,
        sol_price: float,
        sol_client: SolanaClient,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        tx_type: TransactionType,
    ):
        sender_account = accounts[0]
        sol_user = SolanaAccount()
        sol_client.request_airdrop(sol_user.pubkey(), 5 * LAMPORT_PER_SOL)

        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(web3_client)

        user_neon_balance_before = web3_client.get_balance(sender_account)
        move_amount = web3_client._web3.to_wei(5, "ether")
        contract, _ = web3_client.deploy_and_get_contract(
            contract="precompiled/NeonToken",
            version="0.8.10",
            account=sender_account,
            tx_type=tx_type,
        )

        tx = self.web3_client.make_raw_tx(from_=sender_account, amount=move_amount, tx_type=tx_type)

        instruction_tx = contract.functions.withdraw(bytes(sol_user.pubkey())).build_transaction(tx)

        receipt = web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        assert (user_neon_balance_before - web3_client.get_balance(sender_account)) > 5

        balance = sol_client.get_account_info_json_parsed(sol_user.pubkey(), commitment=Commitment("confirmed"))
        assert int(balance.value.lamports) == int(move_amount / 1_000_000_000)

        sol_balance_after = operator.get_solana_balance()
        neon_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        neon_diff = web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after,
            sol_price,
            neon_diff,
            neon_price,
            web3_client.native_token_name,
        )

        get_gas_used_percent(web3_client, receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_withdraw_neon_existing_ata(
        self,
        neon_mint: Pubkey,
        neon_price: float,
        sol_price: float,
        sol_client: SolanaClient,
        solana_account: Keypair,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        withdraw_contract: Contract,
        tx_type: TransactionType,
    ):
        sender_account = accounts[0]

        ata = sol_client.create_associate_token_acc(solana_account, solana_account, neon_mint)
        balances_before = json.loads(sol_client.get_token_account_balance(ata, Commitment("confirmed")).to_json())
        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(web3_client)

        user_neon_balance_before = web3_client.get_balance(sender_account)
        move_amount = web3_client._web3.to_wei(5, "ether")

        tx = web3_client.make_raw_tx(sender_account, amount=move_amount, tx_type=tx_type)
        instruction_tx = withdraw_contract.functions.withdraw(bytes(solana_account.pubkey())).build_transaction(tx)

        receipt = web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        assert (user_neon_balance_before - web3_client.get_balance(sender_account)) > 5

        balances = json.loads(sol_client.get_token_account_balance(ata, Commitment("confirmed")).to_json())
        balance_before = int(balances_before["result"]["value"]["amount"])
        balance_after = int(balances["result"]["value"]["amount"])
        assert balance_after - balance_before == int(move_amount / 1_000_000_000)

        sol_balance_after = operator.get_solana_balance()
        neon_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        neon_diff = web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after,
            sol_price,
            neon_diff,
            neon_price,
            web3_client.native_token_name,
        )
        get_gas_used_percent(web3_client, receipt)

    def test_erc20_transfer(
        self, client_and_price, account_with_all_tokens, web3_client_sol, web3_client, sol_price, operator, faucet
    ):
        """Verify ERC20 token send"""
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        contract = ERC20(w3_client, faucet, owner=account_with_all_tokens)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        acc2 = w3_client.create_account()

        transfer_tx = contract.transfer(account_with_all_tokens, acc2, 25)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)
        get_gas_used_percent(w3_client, transfer_tx)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_deploy_small_contract_less_100tx(
        self,
        account_with_all_tokens: LocalAccount,
        client_and_price: tuple[Web3Client, float],
        web3_client_sol: Web3Client,
        web3_client: NeonChainWeb3Client,
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Verify we are bill minimum for 100 instruction"""
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        contract, _ = w3_client.deploy_and_get_contract(
            contract="common/Counter",
            version="0.8.10",
            account=account_with_all_tokens,
            tx_type=tx_type,
        )

        sol_balance_after_deploy = operator.get_solana_balance()
        token_balance_after_deploy = operator.get_token_balance(w3_client)
        tx = w3_client.make_raw_tx(from_=account_with_all_tokens.address, tx_type=tx_type)

        inc_tx = contract.functions.inc().build_transaction(tx)

        assert contract.functions.get().call() == 0
        receipt = w3_client.send_transaction(account_with_all_tokens, inc_tx)
        assert contract.functions.get().call() == 1

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        assert token_balance_after > token_balance_after_deploy > token_balance_before
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_deploy_to_lost_contract_account(
        self,
        account_with_all_tokens: LocalAccount,
        client_and_price: tuple[Web3Client, float],
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, value=1, tx_type=tx_type)

        with pytest.raises(Web3RPCError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.deploy_and_get_contract(
                contract="common/Counter",
                version="0.8.10",
                account=acc2,
                tx_type=tx_type,
            )

        # estimate required amount for deployment
        contract_interface = helpers.get_contract_interface(
            contract="common/Counter",
            version="0.8.10",
        )

        transaction = w3_client.make_raw_tx(
            from_=acc2,
            data=contract_interface["bin"],
            estimate_gas=True,
            tx_type=tx_type,
        )

        gas = transaction["gas"]
        gas_price = transaction["gasPrice"] if tx_type == TransactionType.LEGACY else transaction["maxFeePerGas"]
        value = int(gas * gas_price) + 1000

        # transfer the required amount to acc2
        w3_client.send_tokens(
            from_=account_with_all_tokens,
            to=acc2,
            value=value,
            tx_type=tx_type,
        )

        # deploy the contract
        receipt = w3_client.send_transaction(acc2, transaction)
        assert receipt["status"] == 1

        # validate results
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, receipt)

    def test_contract_get_is_free(
        self, counter_contract_two_chain, client_and_price, account_with_all_tokens, operator
    ):
        """Verify that get contract calls is free"""
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        user_balance_before = w3_client.get_balance(account_with_all_tokens)
        assert counter_contract_two_chain.functions.get().call() == 0

        assert w3_client.get_balance(account_with_all_tokens) == user_balance_before

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        assert sol_balance_before == sol_balance_after
        assert token_balance_before == token_balance_after

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_cost_resize_account(
        self,
        neon_price: float,
        sol_price: float,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        tx_type: TransactionType,
    ):
        """Verify how much cost account resize"""
        sender_account = accounts[0]
        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(web3_client)

        contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
            contract="common/IncreaseStorage",
            version="0.8.10",
            account=sender_account,
            tx_type=tx_type,
        )

        sol_balance_before_increase = operator.get_solana_balance()
        neon_balance_before_increase = operator.get_token_balance(web3_client)

        tx = web3_client.make_raw_tx(from_=sender_account, tx_type=tx_type)
        inc_tx = contract.functions.inc().build_transaction(tx)

        instruction_receipt = web3_client.send_transaction(sender_account, inc_tx)

        sol_balance_after = operator.get_solana_balance()
        neon_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_before_increase > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_increase > neon_balance_before, "NEON Balance incorrect"
        neon_diff = web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after,
            sol_price,
            neon_diff,
            neon_price,
            web3_client.native_token_name,
        )
        get_gas_used_percent(web3_client, instruction_receipt)

    def test_contract_interact_1000_steps(
        self,
        counter_contract_two_chain: Contract,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        sol_price: float,
        operator: Operator,
    ):
        """Interact with a contract with more 500 instructions"""
        w3_client, token_price = client_and_price

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        tx = w3_client.make_raw_tx(from_=account_with_all_tokens.address)
        instruction_tx = counter_contract_two_chain.functions.moreInstruction(0, 100).build_transaction(
            tx
        )  # 1086 steps in evm
        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, instruction_receipt)

    @pytest.mark.skip(reason="Trxs without chain_id doesn't have profit with current CI stand configuration")
    def test_contract_interact_1000_steps_no_chain_id(
        self,
        counter_contract: Contract,
        web3_client: Web3Client,
        account_with_all_tokens: LocalAccount,
        sol_price: float,
        operator: Operator,
        neon_price,
    ):
        """Interact with a contract with more 500 instructions, transaction without chain_id"""
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)
        tx = web3_client.make_raw_tx(from_=account_with_all_tokens.address, chain_id=None)
        instruction_tx = counter_contract.functions.moreInstruction(0, 100).build_transaction(tx)
        instruction_tx.pop("chainId")
        instruction_receipt = web3_client.send_transaction(account_with_all_tokens, instruction_tx)
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, neon_price, web3_client.native_token_name
        )
        get_gas_used_percent(web3_client, instruction_receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_contract_interact_500000_steps(
        self,
        counter_contract_two_chain: Contract,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Deploy a contract with more 500000 bpf"""
        w3_client, token_price = client_and_price

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        tx = w3_client.make_raw_tx(from_=account_with_all_tokens.address, tx_type=tx_type)

        instruction_tx = counter_contract_two_chain.functions.moreInstruction(0, 3000).build_transaction(tx)

        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        wait_condition(lambda: sol_balance_before > operator.get_solana_balance())

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, instruction_receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_send_transaction_with_gas_limit_reached(
        self,
        counter_contract_two_chain: Contract,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Transaction with small amount of gas"""
        w3_client, token_price = client_and_price

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        tx = w3_client.make_raw_tx(from_=account_with_all_tokens.address, gas=1000, tx_type=tx_type)
        instruction_tx = counter_contract_two_chain.functions.moreInstruction(0, 100).build_transaction(tx)

        with pytest.raises(Web3RPCError, match=GAS_LIMIT_ERROR):
            w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_after == sol_balance_before, "SOL Balance changes"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_send_transaction_with_insufficient_funds(
        self,
        counter_contract_two_chain: Contract,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Transaction with insufficient funds on balance"""
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        w3_client.send_tokens(from_=account_with_all_tokens, to=acc2, value=100, tx_type=tx_type)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        tx = w3_client.make_raw_tx(from_=acc2.address, tx_type=tx_type)

        instruction_tx = counter_contract_two_chain.functions.moreInstruction(0, 1500).build_transaction(tx)
        with pytest.raises(Web3RPCError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.send_transaction(acc2, instruction_tx)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after, "SOL Balance changed"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_tx_interact_more_1kb(
        self,
        counter_contract_two_chain: Contract,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        """Send to contract a big text (tx more than 1 kb)"""
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        tx = w3_client.make_raw_tx(from_=account_with_all_tokens.address, tx_type=tx_type)

        instruction_tx = counter_contract_two_chain.functions.bigString(BIG_STRING).build_transaction(tx)

        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, instruction_receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_deploy_contract_more_1kb(
        self,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        web3_client: NeonChainWeb3Client,
        web3_client_sol: Web3Client,
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        w3_client, token_price = client_and_price

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            contract="common/Fat",
            version="0.8.10",
            account=account_with_all_tokens,
            tx_type=tx_type,
        )

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, contract_deploy_tx)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_deploy_contract_to_payed(
        self,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        web3_client: NeonChainWeb3Client,
        web3_client_sol: Web3Client,
        sol_price: float,
        operator: Operator,
        accounts: EthAccounts,
        tx_type: TransactionType,
    ):
        sender_account = accounts[0]
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        nonce = w3_client.eth.get_transaction_count(account_with_all_tokens.address)
        contract_address = w3_client.keccak(rlp.encode((bytes.fromhex(sender_account.address[2:]), nonce)))[-20:]

        w3_client.send_tokens(
            from_=account_with_all_tokens,
            to=w3_client.to_checksum_address(contract_address.hex()),
            value=5000,
            tx_type=tx_type,
        )

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            contract="common/Counter",
            version="0.8.10",
            account=account_with_all_tokens,
            tx_type=tx_type,
        )

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, contract_deploy_tx)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_deploy_contract_to_exist_unpayed(
        self,
        client_and_price: tuple[Web3Client, float],
        account_with_all_tokens: LocalAccount,
        web3_client: NeonChainWeb3Client,
        web3_client_sol: Web3Client,
        sol_price: float,
        operator: Operator,
        tx_type: TransactionType,
    ):
        w3_client, token_price = client_and_price

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        nonce = w3_client.eth.get_transaction_count(account_with_all_tokens.address)
        contract_address = w3_client.to_checksum_address(
            w3_client.keccak(rlp.encode((bytes.fromhex(account_with_all_tokens.address[2:]), nonce)))[-20:].hex()
        )
        with pytest.raises(Web3RPCError, match=GAS_LIMIT_ERROR):
            w3_client.send_tokens(
                from_=account_with_all_tokens,
                to=contract_address,
                value=100,
                gas=1,
                tx_type=tx_type,
            )

        _, contract_deploy_tx = w3_client.deploy_and_get_contract(
            contract="common/Counter",
            version="0.8.10",
            account=account_with_all_tokens,
            tx_type=tx_type,
        )

        sol_balance_after_deploy = operator.get_solana_balance()
        token_balance_after_deploy = operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after_deploy
        assert token_balance_after_deploy > token_balance_before
        token_diff = w3_client.to_main_currency(token_balance_after_deploy - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after_deploy,
            sol_price,
            token_diff,
            token_price,
            w3_client.native_token_name,
        )
        get_gas_used_percent(w3_client, contract_deploy_tx)

    @pytest.mark.slow
    @pytest.mark.timeout(16 * Time.MINUTE)
    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_trx_alt_on(
        self,
        sol_client: SolanaClient,
        neon_price: float,
        sol_price: float,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        alt_contract: Contract,
        tx_type: TransactionType,
    ):
        """Trigger transaction than requires more than 30 accounts"""
        sender_account = accounts[1]
        accounts_quantity = 45
        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(web3_client)
        tx = web3_client.make_raw_tx(from_=sender_account, tx_type=tx_type)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender_account, instr)
        assert receipt["status"] == 1

        check_alt_on(web3_client, sol_client, receipt)
        wait_until_alt_deleted(web3_client, sol_client, receipt)

        sol_balance_after = operator.get_solana_balance()
        neon_balance_after = operator.get_token_balance(web3_client)
        assert sol_balance_before != sol_balance_after
        assert neon_balance_after > neon_balance_before
        neon_diff = web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after,
            sol_price,
            neon_diff,
            neon_price,
            web3_client.native_token_name,
        )

        get_gas_used_percent(web3_client, receipt)

    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_trx_with_big_amount_of_accounts_alt_off(
        self,
        sol_client: SolanaClient,
        neon_price: float,
        sol_price: float,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        alt_contract: Contract,
        tx_type: TransactionType,
    ):
        # see logs by hash, try with new account
        # if no fails - other tests interference
        """Trigger transaction than requires less than 30 accounts"""
        accounts_quantity = 30
        sender = accounts[1]
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        tx = web3_client.make_raw_tx(from_=sender.address, tx_type=tx_type)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender, instr)
        check_alt_off(web3_client, sol_client, receipt)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after,
            sol_price,
            token_diff,
            neon_price,
            web3_client.native_token_name,
        )
        get_gas_used_percent(web3_client, receipt)

    def test_deploy_big_contract_with_structures(
        self, client_and_price, web3_client, web3_client_sol, account_with_all_tokens, sol_price, operator
    ):
        w3_client, token_price = client_and_price

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        contract, receipt = w3_client.deploy_and_get_contract("EIPs/ERC3475", "0.8.10", account_with_all_tokens)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, token_price, w3_client.native_token_name
        )
        get_gas_used_percent(w3_client, receipt)

    @pytest.mark.eip_1559
    def test_deploy_big_contract_with_structures_eip_1559(
        self,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        neon_price: float,
        sol_price: float,
        operator: Operator,
    ):
        sender_account = accounts[3]

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        contract, receipt = web3_client.deploy_and_get_contract(
            contract="EIPs/ERC3475",
            version="0.8.10",
            account=sender_account,
            tx_type=TransactionType.EIP_1559,
        )

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, neon_price, web3_client.native_token_name
        )
        get_gas_used_percent(web3_client, receipt)

    @pytest.mark.timeout(30 * Time.MINUTE)
    @pytest.mark.slow
    @pytest.mark.parametrize("value", [20, 30])
    @pytest.mark.parametrize("tx_type", TransactionType)
    @pytest.mark.eip_1559
    def test_call_contract_with_mapping_updating(
        self,
        account_with_all_tokens: LocalAccount,
        sol_price: float,
        neon_price: float,
        web3_client: NeonChainWeb3Client,
        sol_client: SolanaClient,
        value: int,
        operator: Operator,
        mapping_actions_contract: Contract,
        tx_type: TransactionType,
    ):
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        tx = web3_client.make_raw_tx(from_=account_with_all_tokens.address, tx_type=tx_type)

        instruction_tx = mapping_actions_contract.functions.replaceValues(value).build_transaction(tx)
        receipt = web3_client.send_transaction(account_with_all_tokens, instruction_tx)
        assert receipt["status"] == 1
        wait_condition(lambda: sol_balance_before != operator.get_solana_balance())

        wait_until_alt_deleted(web3_client, sol_client, receipt)
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, neon_price, web3_client.native_token_name
        )

    @pytest.mark.eip_1559
    def test_eip_1559_small_priority_fee(
        self,
        client_and_price: tuple[Web3Client, float],
        operator: Operator,
        account_with_all_tokens: LocalAccount,
        sol_price: float,
    ):
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)

        last_block = w3_client._web3.eth.get_block(block_identifier="latest")
        base_fee_per_gas = last_block.baseFeePerGas  # noqa
        gas_price = w3_client.gas_price()
        assert base_fee_per_gas == gas_price

        recipient = w3_client.create_account()
        transfer_value = 10

        receipt = w3_client.send_tokens_eip_1559(
            from_=account_with_all_tokens,
            to=recipient,
            value=transfer_value,
            max_priority_fee_per_gas=10,
            max_fee_per_gas=base_fee_per_gas,
        )
        assert receipt["status"] == 1, "Transaction failed"
        wait_condition(lambda: sol_balance_before != operator.get_solana_balance())

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after, "Operator SOL balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, w3_client.native_token_name)
        get_gas_used_percent(w3_client, receipt)

    @pytest.mark.parametrize("gas_multiplier", [1, 5])
    def test_write_large_trx_to_holder(self, web3_client, accounts, operator, sol_price, neon_price, gas_multiplier):
        """The transaction calls ~130 WriteToHolder instructions"""
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        transaction = web3_client.make_raw_tx(
            from_=accounts[0], to=accounts[1], amount=0, estimate_gas=True, data=gen_hash_of_block(120000)
        )
        transaction["gas"] = int(transaction["gas"] * gas_multiplier)

        receipt = web3_client.send_transaction(accounts[0], transaction)
        assert receipt["status"] == 1

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        assert sol_balance_before > sol_balance_after, "Operator SOL balance incorrect"
        sol_diff = sol_balance_before - sol_balance_after

        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, neon_price, web3_client.native_token_name)

    @pytest.mark.skip(reason="https://neonlabs.atlassian.net/browse/NDEV-3710")
    def test_write_large_trx_to_holder_with_small_gas_value(
        self, web3_client, accounts, operator, sol_price, neon_price
    ):
        """The transaction calls ~130 WriteToHolder instructions and fails with out of gas"""
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        transaction = web3_client.make_raw_tx(
            from_=accounts[0], to=accounts[1], amount=0, estimate_gas=True, data=gen_hash_of_block(120000)
        )
        transaction["gas"] = int(transaction["gas"] // 2)

        signed_tx = web3_client.eth.account.sign_transaction(transaction, accounts[0].key)
        transaction_hash = web3_client.eth.send_raw_transaction(signed_tx.raw_transaction)
        allure.attach(f"Transaction hash: {transaction_hash.hex()}", "Transaction hash", allure.attachment_type.TEXT)
        time.sleep(60 * 2)  # wait for transaction to be processed

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        assert sol_balance_before > sol_balance_after, "Operator SOL balance incorrect"
        sol_diff = sol_balance_before - sol_balance_after

        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, neon_price, web3_client.native_token_name)

    def test_check_iterative_trx_with_different_gas_limit_values(
        self,
        counter_contract: Contract,
        web3_client,
        neon_price,
        accounts,
        sol_price: float,
        operator: Operator,
    ):
        tx = web3_client.make_raw_tx(from_=accounts[0].address, tx_type=TransactionType.EIP_1559)
        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = web3_client.send_transaction(accounts[0], instruction_tx)
        assert receipt["status"] == 1

        gas_used = receipt["gasUsed"]
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        while receipt["status"] != 0:
            gas = gas_used // 2
            tx = web3_client.make_raw_tx(from_=accounts[0].address, tx_type=TransactionType.EIP_1559, gas=gas)
            instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
            receipt = web3_client.send_transaction(accounts[0], instruction_tx)

            sol_balance_after = operator.get_solana_balance()
            token_balance_after = operator.get_token_balance(web3_client)

            assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
            assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

            token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
            assert_profit(
                sol_balance_before - sol_balance_after, sol_price, token_diff, neon_price, web3_client.native_token_name
            )

            sol_balance_before = sol_balance_after
            token_balance_before = token_balance_after
            gas_used = gas

    @pytest.mark.parametrize("is_dependent", [True, False])
    def test_multiple_scheduled_trx(
        self,
        operator,
        web3_client_sol,
        neon_user,
        increase_storage_contract,
        evm_loader,
        treasury_pool,
        sol_price,
        sol_client,
        is_dependent,
    ):
        trx_count = 4
        data = decode_function_signature("incWithoutALT()")

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        trx_estimate_obj_list = []
        for i in range(trx_count):
            child_transaction = None if is_dependent else "0xFFFF"
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address,
                    increase_storage_contract.address,
                    data,
                    child_transaction=child_transaction,
                )
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        for i in range(trx_count):
            child_transaction = i + 1 if is_dependent and i != trx_count - 1 else 0xFFFF
            success_limit = 1 if is_dependent and i != 0 else 0
            tree_acc_data.add_trx(trxs[i], child_transaction, success_limit)

        evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)
        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_multiple_scheduled_trx_with_failed_trx(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        revert_contract_caller,
        event_caller_contract,
        evm_loader,
        operator,
        sol_price,
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = decode_function_signature("doAssert()")
        call_data_trx1 = decode_function_signature("indexedArgs()")

        trxs = []
        for i, call_data in enumerate([call_data_trx0, call_data_trx1]):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=revert_contract_caller.address,
                    call_data=call_data,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    chain_id=web3_client_sol.chain_id,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 1)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

        web3_client_sol.send_all_scheduled_transactions(trxs)
        resp2 = web3_client_sol.wait_for_transaction_receipt(trxs[1].hash(), timeout=180)
        assert resp2["status"] == 0

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)
        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_for_erc20_for_spl(
        self,
        web3_client_sol,
        neon_user,
        erc20_spl_mintable,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
    ):
        recipient = NeonUser(evm_loader.loader_id)

        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, 800)

        top_up_in_trx = 400
        amount_to_recipient = 400

        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_0, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_1, child_transaction=hex(3)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_2, child_transaction="0xFFFF"
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_3, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)
        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_solana_interoperability_iterative_tx_eip_1559(
        self, call_solana_caller, sol_client, solana_account, web3_client, accounts, operator, sol_price
    ):
        iterations = 5
        sender = accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        serialized_instruction, mint, _ = prepare_transfer_spl_data(
            sol_client, from_wallet, to_wallet, amount, call_solana_caller
        )
        tx = web3_client.make_raw_tx(from_=sender.address, tx_type=TransactionType.EIP_1559)
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        instruction_tx = call_solana_caller.functions.executeInIterativeMode(
            iterations, 0, serialized_instruction
        ).build_transaction(tx)

        resp = web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        token_price = web3_client.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client.native_token_name)

    def test_solana_interoperability_call_inside_iterative_actions(
        self,
        counter_resource_address: bytes,
        call_solana_caller,
        web3_client,
        sol_price,
        sol_client,
        accounts,
        operator,
    ):
        sender = accounts[0]
        matrix_length = 8
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.solanaCallInsideActionWithMatrix(
            1, matrix, 0, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)
        token_price = web3_client.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client.native_token_name)
