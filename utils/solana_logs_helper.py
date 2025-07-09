import base64
import json

import base58
from solana.rpc.commitment import Confirmed
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from utils.web3client import Web3Client


def decode_logs(log_messages: list) -> str:
    decoded_logs = ""

    for log in log_messages:
        if "Program data:" in log:
            decoded_logs += "Program data: "
            encoded_part = log.replace("Program data: ", "")
            for item in encoded_part.split(" "):
                decoded_logs += " " + str(base64.b64decode(item))
        else:
            decoded_logs += log
        decoded_logs += " "
    return decoded_logs


def get_total_gas_used(resp: GetTransactionResp) -> int | None:
    logs = json.loads(resp.to_json())["result"]["meta"]["logMessages"]

    gas_values = []
    for log in logs:
        if "Program data:" in log:
            encoded_part = log.replace("Program data: ", "")
            for item in encoded_part.split(" "):
                gas_values.append(base64.b64decode(item))

    if b"GAS" in gas_values:
        look_up_index = gas_values.index(b"GAS") + 1
        gas_values = gas_values[look_up_index : look_up_index + 2]
        return [int.from_bytes(value, byteorder="little") for value in gas_values][-1]

    return None


def get_all_solana_logs_for_neon_trx(web3_client: Web3Client, solana_client, trx_hash):
    sol_trxs = web3_client.get_solana_trx_by_neon(trx_hash)["result"]
    logs = []
    for trx in sol_trxs:
        encoded_log = solana_client.get_transaction(
            Signature.from_string(trx), commitment=Confirmed
        ).value.transaction.meta.log_messages
        logs.append(decode_logs(encoded_log))

    return logs


def get_solana_trx_cancel_reason(web3_client: Web3Client, solana_client, trx_hash):
    sol_trxs = web3_client.get_solana_trx_by_neon(trx_hash)["result"]
    cancel_sol_trx_hash = sol_trxs[-1]

    last_trx = solana_client.get_transaction(Signature.from_string(cancel_sol_trx_hash), commitment=Confirmed)
    if "Program log: Instruction: Cancel Transaction" in last_trx.value.transaction.meta.log_messages:
        cancel_data = last_trx.value.transaction.transaction.message.instructions[-1].data
        return base58.b58decode(cancel_data)
    return None
