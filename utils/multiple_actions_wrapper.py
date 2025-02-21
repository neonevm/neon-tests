from solders.pubkey import Pubkey
from web3.types import TxReceipt

from . import stats_collector
from .types import Contract
from .web3client import Web3Client

INIT_TOKEN_AMOUNT = 1000000000000000


@stats_collector.cost_report_from_receipt
def transfer_five_times(
    web3_client: Web3Client, contract: Contract, signer, address_to: Pubkey, amount: list, gas_price=None, gas=None
) -> TxReceipt:
    tx = web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
    transfer_amount_1, transfer_amount_2, transfer_amount_3, transfer_amount_4, transfer_amount_5 = amount
    instruction_tx = contract.functions.transferFiveTimes(
        address_to,
        transfer_amount_1,
        transfer_amount_2,
        transfer_amount_3,
        transfer_amount_4,
        transfer_amount_5,
    ).build_transaction(tx)
    resp = web3_client.send_transaction(signer, instruction_tx)
    return resp
