import typing as tp

from web3 import types

from integration.tests.basic.helpers.assert_message import AssertMessage


def is_hex(hex_data: str) -> bool:
    try:
        int(hex_data, 16)
        return True
    except (ValueError, TypeError):
        return False

def assert_block_fields(block: dict, full_trx: bool, tx_receipt: tp.Optional[types.TxReceipt],
                        pending: bool = False):
    assert "error" not in block
    assert "result" in block, AssertMessage.DOES_NOT_CONTAIN_RESULT
    result = block["result"]
    expected_hex_fields = ["difficulty", "extraData", "gasLimit", "gasUsed", "hash", "logsBloom", "miner",
                           "mixHash", "nonce", "number", "parentHash", "receiptsRoot", "sha3Uncles", "size",
                           "stateRoot", "timestamp", "totalDifficulty", "transactionsRoot"]
    if pending:
        for i in ["hash", "nonce", "miner"]:
            expected_hex_fields.remove(i)
    for field in expected_hex_fields:
        assert is_hex(result[field]), f"Field {field} must be hex but '{result[field]}'"
    if tx_receipt is not None:
        assert result["hash"] == tx_receipt.blockHash.hex(), \
            f"Actual:{result['hash']}; Expected: {tx_receipt.blockHash.hex()}"
        assert result["number"] == hex(tx_receipt.blockNumber), \
            f"Actual:{result['number']}; Expected: {hex(tx_receipt.blockNumber)}"
        assert int(result["gasUsed"], 16) >= int(hex(tx_receipt.gasUsed), 16), \
            f"Actual:{result['gasUsed']} or more; Expected: {hex(tx_receipt.gasUsed)}"
    assert result["uncles"] == []
    transactions = result["transactions"]
    if full_trx:
        if tx_receipt is not None:
            assert tx_receipt.transactionHash.hex() in [transaction["hash"] for transaction in
                                                        transactions], "Created transaction should be in block"
        for transaction in transactions:
            expected_hex_fields = ["hash", "nonce", "blockHash", "blockNumber", "transactionIndex", "from",
                                   "value", "gas", "gasPrice", "v", "r", "s"]
            for field in expected_hex_fields:
                assert is_hex(transaction[field]), f"field '{field}' is not correct. Actual : {transaction[field]}"
            if tx_receipt is not None:
                if tx_receipt.transactionHash.hex() == transaction["hash"]:
                    assert transaction["from"].upper() == tx_receipt['from'].upper()
                    assert transaction["to"].upper() == tx_receipt['to'].upper()
                    # FIXME: fix next assert if input field should have hex value
                    assert transaction["input"] == '0x'
    else:
        for transaction in transactions:
            assert is_hex(transaction)
        if tx_receipt is not None:
            assert tx_receipt.transactionHash.hex() in transactions, "Created transaction should be in block"


def assert_log_field_in_neon_trx_receipt(responce, events_count):
    logs = responce["result"]["logs"]
    assert_neon_logs(logs)
    expected_event_types = ["ENTER CALL"]
    for i in range(events_count):
        expected_event_types.append("LOG")
    expected_event_types.append("EXIT STOP")
    expected_event_types.append("RETURN")

    event_types = [log["neonEventType"] for log in sorted(logs, key=lambda x: int(x["neonEventOrder"], 0))]

    assert event_types == expected_event_types, f"Actual: {event_types}; Expected: {expected_event_types}"


def assert_neon_logs(logs):
    expected_hex_fields = ["neonIxIdx", "neonEventLevel", "neonEventOrder", "transactionHash", "blockHash",
                           "blockNumber", "transactionIndex"]

    for item in logs:
        for field in expected_hex_fields:
            assert is_hex(item[field]), f"field {field} is not correct. Actual : {item[field]}"
