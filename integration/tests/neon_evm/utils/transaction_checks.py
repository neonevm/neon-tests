import allure
from solana.rpc.commitment import Confirmed
from solders.rpc.responses import GetTransactionResp, SendTransactionResp

from utils.logger import log_text_to_allure_and_stdout
from utils.solana_client import SolanaClient
from utils.solana_logs_helper import decode_logs


@allure.step("Check transaction logs contain text")
def check_transaction_logs_have_text(
    solana_client: SolanaClient, trx: GetTransactionResp | SendTransactionResp, text: str
) -> None:
    if isinstance(trx, GetTransactionResp):
        receipt = trx
    else:
        receipt = solana_client.get_transaction(trx, commitment=Confirmed)
    logs = decode_logs(receipt.value.transaction.meta.log_messages)
    log_text_to_allure_and_stdout("Decoded logs", logs)

    assert text in logs, f"Transaction logs don't contain '{text}'. Logs: {logs}"


@allure.step("Check holder account tag")
def check_holder_account_tag(solana_client: SolanaClient, storage_account, layout, expected_tag):
    account_data = solana_client.get_account_info(storage_account, commitment=Confirmed).value.data
    parsed_data = layout.parse(account_data)
    assert parsed_data.tag == expected_tag, f"Account tag {account_data[0]} != expected {expected_tag}"


@allure.step("Check transaction logs do not contain text")
def check_transaction_logs_have_not_text(
    solana_client: SolanaClient, trx: GetTransactionResp | SendTransactionResp, text: str
) -> None:
    if isinstance(trx, GetTransactionResp):
        receipt = trx
    else:
        receipt = solana_client.get_transaction(trx)
    logs = decode_logs(receipt.value.transaction.meta.log_messages)
    assert text not in logs, f"Transaction logs shouldn't contain '{text}'. Logs: {logs}"
