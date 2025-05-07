import json
import os
import time
from decimal import Decimal

import allure
import pytest
import rlp
from _pytest.config import Config
from eth_account.signers.local import LocalAccount
from solders.keypair import Keypair as SolanaAccount
from solders.pubkey import Pubkey
from solana.rpc.types import Commitment
from solana.transaction import Transaction
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)
from web3.contract import Contract
from web3.exceptions import Web3RPCError

from utils import helpers
from utils.accounts import EthAccounts
from utils.consts import LAMPORT_PER_SOL, Time
from utils.erc20 import ERC20
from utils.helpers import wait_condition, gen_hash_of_block
from utils.operator import Operator
from utils.solana_client import SolanaClient
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client, Web3Client
from .const import INSUFFICIENT_FUNDS_ERROR, GAS_LIMIT_ERROR, BIG_STRING
from .steps import (
    assert_profit,
    get_gas_used_percent,
    check_alt_off,
    check_alt_on,
    wait_until_alt_deleted,
)

from ..basic.helpers.chains import make_nonce_the_biggest_for_chain


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

    def test_send_neon_token_without_chain_id(
        self, account_with_all_tokens, web3_client, sol_price, operator, neon_price, faucet
    ):
        # for neon token transactions without chain_id NeonEVM execute it inside NEON network
        # checks eip1820
        # for a transaction without chain_id users need in 1000 times more neon tokens for the execution
        faucet.request_neon(account_with_all_tokens.address, 10000)
        acc2 = web3_client.create_account()
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)

        instruction_tx = web3_client.make_raw_tx(account_with_all_tokens.address, acc2.address, 1000, estimate_gas=True)

        instruction_tx.pop("chainId")

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

    def test_erc20wrapper_transfer(self, erc20_wrapper, client_and_price, sol_price, operator, accounts):
        sender_account = accounts[0]
        w3_client, token_price = client_and_price
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(w3_client)
        assert erc20_wrapper.contract.functions.balanceOf(sender_account.address).call() == 0
        transfer_tx = erc20_wrapper.transfer(erc20_wrapper.account, sender_account, 25)

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
        pytestconfig: Config,
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
        pytestconfig: Config,
        neon_mint: Pubkey,
        neon_price: float,
        sol_price: float,
        sol_client: SolanaClient,
        operator: Operator,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        withdraw_contract: Contract,
        tx_type: TransactionType,
    ):
        sender_account = accounts[0]
        sol_user = SolanaAccount()
        sol_client.request_airdrop(sol_user.pubkey(), 5 * LAMPORT_PER_SOL)

        wait_condition(lambda: sol_client.get_balance(sol_user.pubkey()) != 0)

        trx = Transaction()
        trx.add(create_associated_token_account(sol_user.pubkey(), sol_user.pubkey(), neon_mint))

        sol_client.send_tx_and_check_status_ok(trx, sol_user)

        dest_token_acc = get_associated_token_address(sol_user.pubkey(), neon_mint)

        sol_balance_before = operator.get_solana_balance()
        neon_balance_before = operator.get_token_balance(web3_client)

        user_neon_balance_before = web3_client.get_balance(sender_account)
        move_amount = web3_client._web3.to_wei(5, "ether")

        tx = web3_client.make_raw_tx(sender_account, amount=move_amount, tx_type=tx_type)
        instruction_tx = withdraw_contract.functions.withdraw(bytes(sol_user.pubkey())).build_transaction(tx)

        receipt = web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        assert (user_neon_balance_before - web3_client.get_balance(sender_account)) > 5

        balances = json.loads(sol_client.get_token_account_balance(dest_token_acc, Commitment("confirmed")).to_json())
        assert int(balances["result"]["value"]["amount"]) == int(move_amount / 1_000_000_000)

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

    @pytest.mark.xfail(reason="https://neonlabs.atlassian.net/browse/NDEV-699")
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
        """Deploy a contract with more 500 instructions"""
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

        check_alt_on(web3_client, sol_client, receipt)
        wait_until_alt_deleted(web3_client, sol_client, receipt)
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

    # @pytest.mark.skip(reason="work incorrect very often")
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

    @pytest.mark.skip(reason="work incorrect very often")
    @pytest.mark.eip_1559
    def test_eip_1559_zero_priority_fee(
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
            max_priority_fee_per_gas=0,
            max_fee_per_gas=base_fee_per_gas,
        )

        assert w3_client.get_balance(recipient) == transfer_value

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

    def test_iterative_failed_canceled_trx_with_out_of_gas(
        self,
        counter_contract: Contract,
        web3_client,
        neon_price,
        accounts,
        sol_price: float,
        operator: Operator,
    ):
        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client)
        tx = web3_client.make_raw_tx(from_=accounts[0].address, tx_type=TransactionType.EIP_1559)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = web3_client.send_transaction(accounts[0], instruction_tx)
        assert receipt["status"] == 1

        gas_used = receipt["gasUsed"]
        print("Gas used: ", gas_used)

        tx = web3_client.make_raw_tx(from_=accounts[0].address, tx_type=TransactionType.EIP_1559, gas=gas_used // 100)
        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = web3_client.send_transaction(accounts[0], instruction_tx)
        print("Failed tx receipt: ", receipt)
        assert receipt["status"] == 0

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

        token_diff = web3_client.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(
            sol_balance_before - sol_balance_after, sol_price, token_diff, neon_price, web3_client.native_token_name
        )
