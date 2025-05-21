import logging
import time
from decimal import Decimal

import allure
from solana.rpc.commitment import Confirmed
from solana.rpc.core import RPCException
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from integration.tests.economy.const import DECIMAL_CONTEXT
from utils.consts import LAMPORT_PER_SOL, Time
from utils.helpers import wait_condition, hasattr_recursive
from utils.solana_data_for_neon_trx_helper import get_alt_by_neon_trx

logger = logging.getLogger(__name__)


@allure.step("Verify operator profit")
def assert_profit(sol_diff, sol_price, token_diff, token_price, token_name):
    expense_lamports = sol_diff / LAMPORT_PER_SOL
    if token_diff < 0:
        raise AssertionError(f"NEON has negative difference {token_diff}")
    expense_usd = Decimal(expense_lamports, DECIMAL_CONTEXT) * Decimal(sol_price, DECIMAL_CONTEXT)
    revenue_usd = Decimal(token_diff, DECIMAL_CONTEXT) * Decimal(token_price, DECIMAL_CONTEXT)
    profit_usd = revenue_usd - expense_usd
    profit_percentage = profit_usd / expense_usd * 100

    log_level = logging.WARNING if profit_percentage < 2 else logging.INFO
    logger.log(level=log_level, msg=f"Operator income: {profit_percentage}%")

    msg = "Operator receive {:.9f} {} ({:.2f} $) and spend {:.9f} SOL ({:.2f} $), profit: {:.9f}% ".format(
        token_diff,
        token_name,
        revenue_usd,
        expense_lamports,
        expense_usd,
        profit_percentage,
    )
    with allure.step(msg):
        assert revenue_usd > expense_usd, msg


@allure.step("Check transaction used ALT")
def check_alt_on(web3_client, sol_client, receipt):
    alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
    assert alt is not None, "There are no lookup table for transaction"


@allure.step("Check transaction not used ALT")
def check_alt_off(web3_client, sol_client, receipt):
    alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
    assert alt is None, "Lookup table is used for transaction"


@allure.step("Wait until ALT will be deleted")
def wait_until_alt_deleted(web3_client, sol_client, receipt):
    alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
    wait_condition(
        lambda: not sol_client.account_exists(alt),
        timeout_sec=10 * Time.MINUTE,
        delay=3,
    )


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


@allure.step("Get solana transaction with ALT")
def get_sol_trx_with_alt(web3_client, sol_client, web3_transaction_receipt):
    solana_trx = web3_client.get_solana_trx_by_neon(web3_transaction_receipt["transactionHash"].hex())
    sol_trx_with_alt = None

    wait_condition(
        lambda: sol_client.get_transaction(
            Signature.from_string(solana_trx["result"][0]), max_supported_transaction_version=0, commitment=Confirmed
        )
        != GetTransactionResp(None)
    )

    for trx in solana_trx["result"]:
        trx_sol = sol_client.get_transaction(
            Signature.from_string(trx), max_supported_transaction_version=0, commitment=Confirmed
        )
        if (
            hasattr_recursive(trx_sol, "value.transaction.transaction.message.address_table_lookups")
            and trx_sol.value.transaction.transaction.message.address_table_lookups
        ):
            sol_trx_with_alt = trx_sol
    if not sol_trx_with_alt:
        print(f"There are no lookup table for {solana_trx}")
        return None

    return sol_trx_with_alt
