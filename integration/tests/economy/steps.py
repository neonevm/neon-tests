import time
from decimal import Decimal

import allure
from solana.rpc.core import RPCException
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from integration.tests.economy.const import DECIMAL_CONTEXT, TX_COST
from utils.consts import LAMPORT_PER_SOL
from utils.helpers import wait_condition


@allure.step("Verify operator profit")
def assert_profit(sol_diff, sol_price, token_diff, token_price, token_name):
    sol_amount = sol_diff / LAMPORT_PER_SOL
    if token_diff < 0:
        raise AssertionError(f"NEON has negative difference {token_diff}")
    sol_cost = Decimal(sol_amount, DECIMAL_CONTEXT) * Decimal(sol_price, DECIMAL_CONTEXT)
    token_cost = Decimal(token_diff, DECIMAL_CONTEXT) * Decimal(token_price, DECIMAL_CONTEXT)

    msg = "Operator receive {:.9f} {} ({:.2f} $) and spend {:.9f} SOL ({:.2f} $), profit - {:.9f}% ".format(
        token_diff,
        token_name,
        token_cost,
        sol_amount,
        sol_cost,
        ((token_cost - sol_cost) / sol_cost * 100),
    )
    with allure.step(msg):
        assert token_cost > sol_cost, msg


@allure.step("Get single transaction gas")
def get_single_transaction_gas():
    """One TX_COST to verify Solana signature plus another one TX_COST to pay to Governance"""
    return TX_COST * 2


@allure.step("Check transaction used ALT")
def check_alt_on(web3_client, sol_client, receipt, accounts_quantity):
    solana_trx = web3_client.get_solana_trx_by_neon(receipt["transactionHash"].hex())
    wait_condition(
        lambda: sol_client.get_transaction(
            Signature.from_string(solana_trx["result"][0]),
            max_supported_transaction_version=0,
        )
                != GetTransactionResp(None)
    )
    trx = sol_client.get_transaction(
        Signature.from_string(solana_trx["result"][0]),
        max_supported_transaction_version=0,
    )
    alt = trx.value.transaction.transaction.message.address_table_lookups
    accounts = alt[0].writable_indexes + alt[0].readonly_indexes
    assert len(accounts) == accounts_quantity - 2


@allure.step("Check block for not using ALT")
def check_alt_off(block):
    txs = block.value.transactions
    for tx in txs:
        if tx.version == 0 and tx.transaction.message.address_table_lookups:
            raise AssertionError("ALT should not be used")


@allure.step("Get gas used percent")
def get_gas_used_percent(web3_client, receipt):
    trx = web3_client.eth.get_transaction(receipt["transactionHash"])
    estimated_gas = trx["gas"]
    percent = round(receipt["gasUsed"] / estimated_gas * 100, 2)
    with allure.step(f"Gas used percent: {percent}%"):
        pass


@allure.step("Wait for block")
def wait_for_block(client, block, timeout=60):
    started = time.time()
    while (time.time() - started) < timeout:
        try:
            return client.get_block(block, max_supported_transaction_version=2)
        except RPCException:
            time.sleep(3)
        time.sleep(3)
    raise TimeoutError("Block not available for slot")
