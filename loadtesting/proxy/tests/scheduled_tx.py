import logging

from utils.consts import wSOL
from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success

from locust import User, tag, task
from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)


@tag("scheduled_tx independent")
class ScheduledTxsIndependentTasksSet(NeonProxyTasksSet):
    """Implements Independent Scheduled txs pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

    @task
    def task_send_independent_scheduled_tx(self):
        """Send independent scheduled transactions"""
        neon_user = self.get_neon_user()
        recipient = NeonUser(self.evm_loader.loader_id)

        transfer_amount = 50
        burn_amount = 25
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
                    neon_user.checksum_address,
                    self.erc20_info["erc20_address"],
                    call_data[i],
                    child_transaction="0xFFFF",
                )
            )
        estimate_result = self.web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list
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
            neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=240)


@tag("scheduled_tx dependent")
class ScheduledTxsDependentTasksSet(NeonProxyTasksSet):
    """Implements Dependent Scheduled txs pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

    @task
    def task_send_dependent_scheduled_tx(self):
        """Send independent scheduled transactions"""
        neon_user = self.get_neon_user()
        recipient = NeonUser(self.evm_loader.loader_id)

        top_up_in_trx = 100
        amount_to_recipient = 100

        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [self.erc20_info["erc20_owner_address"], neon_user.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_0, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_1, child_transaction=hex(3)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_2, child_transaction="0xFFFF"
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_3, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = self.web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list
        )

        gas_list_new = []
        for i in estimate_result["gasList"]:
            new_value = 10 * int(i, 16)
            gas_list_new.append(hex(new_value))

        estimate_result["gasList"] = gas_list_new

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

        self.evm_loader.create_tree_account_multiple(
            neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=180)


@tag("scheduled_tx: use pda and ata")
class ScheduledTxsPdaAndAtaUsedTasksSet(NeonProxyTasksSet):
    """Implements Scheduled txs with pda and ata used pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

    @task
    def task_send_scheduled_tx_pda_and_ata_used(self):
        """Send scheduled transactions pda and ata used, two recipients"""
        neon_user = self.get_neon_user()
        recipient_0 = NeonUser(self.evm_loader.loader_id)
        recipient_1 = NeonUser(self.evm_loader.loader_id)

        data_0 = decode_function_signature("transfer(address,uint256)", [recipient_0.checksum_address, 100])
        data_1 = decode_function_signature("transfer(address,uint256)", [recipient_1.checksum_address, 100])

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_0
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, self.erc20_info["erc20_address"], data_1
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1]
        estimate_result = self.web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list
        )

        gas_list_new = []
        for i in estimate_result["gasList"]:
            new_value = 50 * int(i, 16)
            gas_list_new.append(hex(new_value))

        estimate_result["gasList"] = gas_list_new

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)

        self.evm_loader.create_tree_account_multiple(
            neon_user, self.treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=240)


class ScheduledTxUser(User):
    tasks = {
        ScheduledTxsIndependentTasksSet: 1,
        ScheduledTxsDependentTasksSet: 1,
        ScheduledTxsPdaAndAtaUsedTasksSet: 1,
    }
