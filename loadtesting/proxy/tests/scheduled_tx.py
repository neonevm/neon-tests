import logging
import random
import typing as tp

from eth_account import Account
from eth_account.signers.local import LocalAccount
from solders.keypair import Keypair

from utils.consts import wSOL
from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.erc20wrapper import ERC20NewWrapper
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success

from locust import User, tag, task
from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)


@tag("scheduled_tx")
class ScheduledTxTasksSet(NeonProxyTasksSet):
    """Implements Scheduled tx pipeline tasks"""

    erc20: tp.Optional[ERC20NewWrapper] = None

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])
        symbol = self.erc20_info["symbol"]
        account: LocalAccount = Account.from_key(self.erc20_info["owner_key"])
        self.erc20 = ERC20NewWrapper(
            self.web3_client,
            self.faucet,
            f"Test {symbol}",
            symbol,
            self.sol_client,
            solana_account=self.solana_account,
            mintable=True,
            bank_account=self.bank_account,
            contract_address=self.erc20_info["address"],
            account=account,
        )

        self.erc20.mint_tokens(self.erc20.account, self.erc20.account.address)

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    def get_neon_user(self):
        item = random.choice(self.erc20_info["neon_users"])
        account = bytes(item, encoding="raw_unicode_escape")
        return NeonUser(evm_loader_id=self.evm_loader.loader_id, keypair=Keypair.from_bytes(account))

    @task
    def task_send_scheduled_tx(self):
        """Send scheduled transactions"""
        neon_user = self.get_neon_user()
        recipient = self.get_neon_user()

        transfer_amount = 100
        burn_amount = 50
        approve_amount = 1000
        trx_count = 4

        data_0 = decode_function_signature("approve(address,uint256)", [neon_user.checksum_address, approve_amount])
        data_1 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, transfer_amount])
        data_2 = decode_function_signature("burn(uint256)", [burn_amount])
        data_3 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, transfer_amount])

        call_data: list = [data_0, data_1, data_2, data_3]

        trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address, self.erc20.address, call_data[i], child_transaction="0xFFFF"
                )
            )
        estimate_result = self.web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list
        )

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
            neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex())


class ScheduledTxUser(User):
    tasks = {
        ScheduledTxTasksSet: 1,
    }
