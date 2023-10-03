import typing as tp
from types import SimpleNamespace

from hexbytes import HexBytes
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
    expected_hex_fields = ["difficulty", "gasLimit", "gasUsed", "hash", "logsBloom", "miner",
                           "mixHash", "nonce", "number", "parentHash", "receiptsRoot", "sha3Uncles", "size",
                           "stateRoot", "timestamp", "transactionsRoot"]
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
        assert result["extraData"] == '0x'
        assert result["totalDifficulty"] == '0x0'
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
                    assert transaction["input"] == '0x'
    else:
        for transaction in transactions:
            assert is_hex(transaction)
        if tx_receipt is not None:
            assert tx_receipt.transactionHash.hex() in transactions, "Created transaction should be in block"


def assert_log_field_in_neon_trx_receipt(response, events_count):
    expected_event_types = ["ENTER CALL"]
    for i in range(events_count):
        expected_event_types.append("LOG")
    expected_event_types.append("EXIT STOP")
    expected_event_types.append("RETURN")
    all_logs = []

    for trx in response["result"]["solanaTransactions"]:
        expected_hex_fields = ["solanaBlockNumber", "solanaLamportSpent"]
        assert_fields_are_hex(trx, expected_hex_fields)

        assert trx['solanaTransactionIsSuccess'] == True
        instructions = trx["solanaInstructions"]
        assert instructions != []
        for instruction in instructions:
            expected_hex_fields = ["solanaInstructionIndex", "svmHeapSizeLimit",
                                   "svmHeapSizeUsed", "svmCyclesLimit", "svmCyclesUsed", "neonInstructionCode",
                                   "neonAlanIncome", "neonGasUsed", "neonTotalGasUsed"]
            assert_fields_are_hex(instruction, expected_hex_fields)
            assert instruction["solanaProgram"] == "NeonEVM"
            assert instruction["solanaInnerInstructionIndex"] is None
            assert instruction["neonStepLimit"] is None
            neon_logs = instruction["neonLogs"]
            assert neon_logs != []
            for log in neon_logs:
                all_logs.append(log)
    event_types = [log["neonEventType"] for log in sorted(all_logs, key=lambda x: x["neonEventOrder"])]

    assert event_types == expected_event_types, f"Actual: {event_types}; Expected: {expected_event_types}"


def assert_fields_are_hex(object, expected_hex_fields):
    if isinstance(object, SimpleNamespace):
        for field in expected_hex_fields:
            assert hasattr(object, field), f"no expected field {field} in the object"
            assert is_hex(getattr(object, field)), f"field {field} is not correct. Actual : {getattr(object, field)}"
        return

    for field in expected_hex_fields:
        assert field in object, f"no expected field {field} in the object"
        assert is_hex(object[field]), f"field {field} is not correct. Actual : {object[field]}"


def assert_fields_are_boolean(object, expected_boolean_fields):
    for field in expected_boolean_fields:
        assert field in object, f"no expected field {field} in the object"
        assert type(object[field]) == bool, f"field {field} is not boolean. Actual : {type(object[field])}"


def assert_equal_fields(result, comparable_object, comparable_fields, keys_mappings):
    """
    Assert that fields in the result object are equal to fields in comparable_object

    :param result:
    :param comparable_object:
    :param comparable_fields: list of comparable fields
    :param keys_mappings: map name of the field in the result object to the field in comparable_object
    :return:
    """
    for field in comparable_fields:
        l = result[field]
        if keys_mappings and keys_mappings.get(field):
            r = comparable_object[keys_mappings.get(field)]
        else:
            r = comparable_object[field]
        if isinstance(r, str):
            r = r.lower()
        if isinstance(r, int):
            r = hex(r)
        if isinstance(r, HexBytes):
            r = r.hex()
        assert l == r, f"{field} from response {l} is not equal to {field} from receipt {r}"
