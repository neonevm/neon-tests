import logging
import random
import typing as tp
import eth_abi

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import abi

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address

from utils.consts import wSOL
from utils.erc20wrapper import ERC20NewWrapper
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest

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
        return random.choice(self.user.environment.shared.neon_users)

    @task
    def task_send_scheduled_tx(self):
        """Send scheduled transactions"""
        neon_user = self.get_neon_user()
        recipient = self.get_neon_user()

        amount_to_transfer = 1_000

        my_pda = Pubkey(self.erc20.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(self.erc20.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)
        nonce = self.web3_client_sol.get_nonce(neon_user.checksum_address)

        self.erc20.pop_up_balance(
            self.evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
        )

        assert (
            int(self.evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount)
            == amount_to_transfer
        )
        assert (
            int(self.evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount)
            == amount_to_transfer
        )

        transfer_amount = 200
        burn_amount = 100
        approve_amount = 1000
        trx_count = 4
        data_0 = abi.function_signature_to_4byte_selector("approve(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [neon_user.checksum_address, approve_amount]
        )
        data_1 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        data_2 = abi.function_signature_to_4byte_selector("burn(uint256)") + eth_abi.encode(["uint256"], [burn_amount])
        data_3 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        call_data: list = [data_0, data_1, data_2, data_3]

        # TODO Use estimate result method to count transaction fees. Waiting for developers to fix it.
        trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, self.erc20.address, call_data[i])
            )
        estimate_result = self.web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list
        )

        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))
        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 0)

        self.evm_loader.create_tree_account_multiple(
            neon_user,
            self.treasury_pool,
            tree_acc_data.data,
            wSOL["address_spl"],
            chain_id=self.web3_client_sol.chain_id,
        )
        self.web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            assert (
                self.web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)["status"] == 1
            ), f"transaction_{trx.index} failed"

        balance_pda = self.erc20.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_ata = self.erc20.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert self.erc20.get_balance(recipient.checksum_address) == transfer_amount * 2
        assert balance_pda == amount_to_transfer - transfer_amount * 2 - burn_amount
        assert balance_ata == amount_to_transfer


class ScheduledTxUser(User):
    tasks = {
        ScheduledTxTasksSet: 1,
    }
