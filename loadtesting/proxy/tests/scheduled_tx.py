import logging
import os
import string
import threading
import random

import base58
from solana.rpc import commitment

from utils.accounts import EthAccounts
from utils.consts import LAMPORT_PER_SOL, wSOL
from utils.erc20wrapper import ERC20NewWrapper
from utils.evm_loader import EvmLoader
from utils.faucet import Faucet
from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success

from locust import User, tag, task, events, env
from loadtesting.proxy.common.base import NeonProxyTasksSet
from utils.web3client import NeonChainWeb3Client
from solders.keypair import Keypair

LOG = logging.getLogger(__name__)
USER_LOCK = threading.Lock()


@events.test_start.add_listener
def prepare_one_contract_for_scheduled_trx(environment: env.Environment, **kwargs):
    network = "local"
    use_bank = None
    neon_users = environment.parsed_options.num_users
    web3_client = NeonChainWeb3Client(proxy_url=environment.credentials["proxy_url"])
    faucet = Faucet(faucet_url=environment.credentials["faucet_url"], web3_client=web3_client)

    # set bank account if needed
    bank_account = None
    if network != "local" and use_bank:
        if network == "devnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY")
        else:
            raise ValueError("set BANK_PRIVATE_KEY env variable")
        key = base58.b58decode(private_key)
        bank_account = Keypair.from_bytes(key)

    account_manager = EthAccounts(web3_client, faucet, bank_account)

    neon_user_balance = int(10**12 / neon_users)
    environment.contract_info = {}

    evm_loader = EvmLoader(
        program_id=environment.credentials["evm_loader"],
        endpoint=environment.credentials["solana_url"],
        neon_chain_id=environment.credentials["network_ids"]["neon"],
        sol_chain_id=environment.credentials["network_ids"]["sol"],
        neon_token_mint_str=environment.credentials["spl_neon_mint"],
    )

    # create solana account
    solana_account = Keypair()
    if network != "local" and use_bank:
        evm_loader.send_sol(bank_account, solana_account.pubkey(), int(1 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(solana_account.pubkey(), 1 * LAMPORT_PER_SOL)

    # create owner
    eth_account = account_manager.create_account()

    # deploy a new erc20 contract
    print("Start to deploy a contract...")
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20NewWrapper(
        web3_client,
        faucet,
        f"Test {symbol}",
        symbol,
        evm_loader,
        solana_account=solana_account,
        mintable=True,
        bank_account=None,
        account=eth_account,
    )

    print("Mint tokens...")
    erc20.mint_tokens(signer=erc20.account, to_address=erc20.account.address, amount=10**18)

    environment.contract_info["erc20_address"] = erc20.contract.address
    environment.contract_info["erc20_owner_address"] = erc20.account.address

    print("Create neon users...")
    environment.contract_info["accounts"] = []
    for i in range(neon_users):
        neon_solana_account = Keypair()
        environment.contract_info["accounts"].append(bytes(neon_solana_account))
        print(f"Creating {i} neon user...")
        neon_user = NeonUser(evm_loader.loader_id, keypair=neon_solana_account)
        balance = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
        if network not in ["devnet"]:
            if balance < 5 * LAMPORT_PER_SOL:
                evm_loader.request_airdrop(
                    neon_user.solana_account.pubkey(), 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed
                )
        print(f"Pop up {i} neon user balance...")
        erc20.pop_up_balance(
            evm_loader, recipient=neon_user, pda_amount=neon_user_balance, ata_amount=neon_user_balance
        )
        erc20.approve(erc20.account, neon_user.checksum_address, neon_user_balance)


@tag("scheduled_tx independent")
class ScheduledTxsIndependentTasksSet(NeonProxyTasksSet):
    """Implements independent scheduled txs sending pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

        with USER_LOCK:
            if not self.user.environment.contract_info["accounts"]:
                raise RuntimeError("Too little users")
            self.neon_account = self.user.environment.contract_info["accounts"].pop(0)

    def on_stop(self):
        if self.account is not None:
            with USER_LOCK:
                self.user.environment.contract_info["accounts"].append(self.account)
                LOG.info(f"Returned user: {self.account.address}")

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    @task
    def task_send_independent_scheduled_tx(self):
        """Send independent scheduled transactions"""
        self.check_neon_user_balance(self.neon_account.solana_account)
        recipient = self.get_account()

        transfer_amount = 10
        burn_amount = 10
        approve_amount = 100
        trx_count = 4

        data_0 = decode_function_signature(
            "approve(address,uint256)", [self.neon_account.checksum_address, approve_amount]
        )
        data_1 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, transfer_amount])
        data_2 = decode_function_signature("burn(uint256)", [burn_amount])
        data_3 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, transfer_amount])

        call_data: list = [data_0, data_1, data_2, data_3]

        trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    self.neon_account.checksum_address,
                    self.user.environment.contract_info["erc20_address"],
                    call_data[i],
                    child_transaction="0xFFFF",
                )
            )
        estimate_result = self.web3_client_sol.estimate_scheduled(
            self.neon_account.solana_account.pubkey(), trx_estimate_obj_list
        )

        gas_list_new = []
        for i in estimate_result["gasList"]:
            new_value = 10 * int(i, 16)
            gas_list_new.append(hex(new_value))

        estimate_result["gasList"] = gas_list_new

        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 0)

        self.evm_loader.create_tree_account_multiple(
            self.neon_account, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=240)


#
# #
# # @tag("scheduled_tx dependent")
# # class ScheduledTxsDependentTasksSet(NeonProxyTasksSet):
# #     """Implements dependent scheduled txs sending pipeline tasks"""
# #
# #     def on_start(self) -> None:
# #         super().on_start()
# #         super().setup()
# #         self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])
# #
#
# #     @task
# #     def task_send_dependent_scheduled_tx(self):
# #         """Send dependent scheduled transactions"""
# #         neon_user = self.get_neon_user()
# #         self.check_neon_user_balance(neon_user.solana_account)
# #         recipient = self.get_random_neon_user(exclude_user=neon_user)
# #
# #         top_up_in_trx = 10
# #         amount_to_recipient = 10
# #
# #         data_0 = data_1 = decode_function_signature(
# #             "transferFrom(address,address,uint256)",
# #             [self.erc20_info["erc20_owner_address"], neon_user.checksum_address, top_up_in_trx],
# #         )
# #         data_2 = data_3 = decode_function_signature(
# #             "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
# #         )
# #
# #         trx_estimate_0 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_0, child_transaction=hex(2)
# #         )
# #         trx_estimate_1 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_1, child_transaction=hex(3)
# #         )
# #         trx_estimate_2 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_2, child_transaction="0xFFFF"
# #         )
# #         trx_estimate_3 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_3, child_transaction="0xFFFF"
# #         )
# #         trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]
# #
# #         estimate_result = self.web3_client_sol.estimate_scheduled(
# #             neon_user.solana_account.pubkey(), trx_estimate_obj_list
# #         )
# #
# #         gas_list_new = []
# #         for i in estimate_result["gasList"]:
# #             new_value = 10 * int(i, 16)
# #             gas_list_new.append(hex(new_value))
# #
# #         estimate_result["gasList"] = gas_list_new
# #
# #         trxs = []
# #         for i in range(len(trx_estimate_obj_list)):
# #             trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))
# #
# #         tree_acc_data = CreateTreeAccMultipleData(
# #             nonce=estimate_result["nonce"],
# #             max_fee_per_gas=estimate_result["maxFeePerGas"],
# #             max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
# #         )
# #
# #         tree_acc_data.add_trx(trxs[0], 2, 0)
# #         tree_acc_data.add_trx(trxs[1], 3, 0)
# #         tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
# #         tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)
# #
# #         self.evm_loader.create_tree_account_multiple(
# #             neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
# #         )
# #         self.web3_client_sol.send_all_scheduled_transactions(trxs)
# #
# #         for trx in trxs:
# #             check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=180)
# #
# #
# # @tag("scheduled_tx: transfer tokens to two users")
# # class ScheduledTxsTransferToDifferentUsersTasksSet(NeonProxyTasksSet):
# #     """Implements transfer to different users via scheduled txs pipeline tasks"""
# #
# #     def on_start(self) -> None:
# #         super().on_start()
# #         super().setup()
# #         self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])
#
#
# #     @task
# #     def task_send_scheduled_tx_pda_and_ata_used(self):
# #         """Send scheduled transactions: transfer tokens to recipients"""
# #         neon_user = self.get_neon_user()
# #         self.check_neon_user_balance(neon_user.solana_account)
# #         recipient_0 = self.get_random_neon_user(exclude_user=neon_user)
# #         recipient_1 = self.get_random_neon_user(exclude_user=neon_user)
# #
# #         data_0 = decode_function_signature("transfer(address,uint256)", [recipient_0.checksum_address, 10])
# #         data_1 = decode_function_signature("transfer(address,uint256)", [recipient_1.checksum_address, 10])
# #
# #         trx_estimate_0 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_0
# #         )
# #         trx_estimate_1 = ScheduledTrxEstimateRequest(
# #             neon_user.checksum_address, self.erc20_info["erc20_address"], data_1
# #         )
# #         trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1]
# #         estimate_result = self.web3_client_sol.estimate_scheduled(
# #             neon_user.solana_account.pubkey(), trx_estimate_obj_list
# #         )
# #
# #         gas_list_new = []
# #         for i in estimate_result["gasList"]:
# #             new_value = 50 * int(i, 16)
# #             gas_list_new.append(hex(new_value))
# #
# #         estimate_result["gasList"] = gas_list_new
# #
# #         trxs = []
# #         for i in range(len(trx_estimate_obj_list)):
# #             trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))
# #
# #         tree_acc_data = CreateTreeAccMultipleData(
# #             nonce=estimate_result["nonce"],
# #             max_fee_per_gas=estimate_result["maxFeePerGas"],
# #             max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
# #         )
# #
# #         tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
# #         tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
# #
# #         self.evm_loader.create_tree_account_multiple(
# #             neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
# #         )
# #         self.web3_client_sol.send_all_scheduled_transactions(trxs)
# #         for trx in trxs:
# #             check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=240)
# #
# #
class ScheduledTxUser(User):
    tasks = {
        ScheduledTxsIndependentTasksSet: 1,
        # ScheduledTxsDependentTasksSet: 1,
        # ScheduledTxsTransferToDifferentUsersTasksSet: 1,
    }
