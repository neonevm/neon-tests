import logging
from decimal import Decimal
import pytest
import allure
from eth_account.signers.local import LocalAccount


from integration.tests.economy.const import DECIMAL_CONTEXT
from utils.consts import (
    LAMPORT_PER_SOL,
    Time,
    PAYMENT_FOR_TRX_FINISHING,
    PAYMENT_FOR_TREE_ACCOUNT_DELETING,
    TRX_EXECUTION_PRICE,
    TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST,
    LAMPORT_TO_INNER_SOL,
)
from utils.helpers import wait_condition
from utils.neon_user import NeonUser
from utils.operator import Operator
from utils.solana_data_for_neon_trx_helper import get_alt_by_neon_trx
from utils.web3client import Web3Client

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
    if alt is not None:
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


@allure.step("Calculate additional sol expenses")
def calculate_additional_expenses(trx_count):
    return (
        PAYMENT_FOR_TREE_ACCOUNT_DELETING
        + TRX_EXECUTION_PRICE
        + PAYMENT_FOR_TRX_FINISHING * trx_count
        + TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST
    ) * LAMPORT_TO_INNER_SOL


@allure.step("Summarize operator, sender and receivers account balances inside neon")
def sum_balances(w3_client: Web3Client, operator: Operator, accounts: list[NeonUser | str | LocalAccount]) -> int:
    token_sum = operator.get_token_balance(w3_client)
    for account in accounts:
        account = account.checksum_address if isinstance(account, NeonUser) else account
        token_sum += w3_client.get_balance(account)
    return token_sum


@allure.step("Check total volume of tokens inside neon remains unchanged after transaction")
def assert_tokens_volumes_stayed_same(sum_of_tokens_before: int, sum_of_tokens_after: int):
    if sum_of_tokens_before != sum_of_tokens_after:
        diff = sum_of_tokens_after - sum_of_tokens_before
        direction = "LOWER" if diff < 0 else "MORE"
        pytest.fail(
            f"Token volume became {direction} than before. "
            f"sum_of_tokens_before={sum_of_tokens_before}, "
            f"sum_of_tokens_after={sum_of_tokens_after}, "
            f"Diff={diff}"
        )
