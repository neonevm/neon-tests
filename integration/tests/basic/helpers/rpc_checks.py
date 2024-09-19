import typing as tp
from collections import Counter
from types import SimpleNamespace

from hexbytes import HexBytes
from web3 import types

from clickfile import EnvName
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import NeonEventType, SolanaInstruction
from utils.models.result import NeonGetTransactionResult, SolanaByNeonTransaction

NoneType = type(None)


def is_hex(hex_data: str) -> bool:
    if hex_data == "0x":
        return True
    try:
        int(hex_data, 16)
        return True
    except (ValueError, TypeError):
        return False


def hex_str_consists_not_only_of_zeros(hex_data: str) -> bool:
    """Helps to verify that long response hex str data is not consists of just zeros"""
    t = hex_data
    if t.startswith("0x"):
        t = hex_data.split("0x")[1]
    for c in t:
        if c != "0":
            return True
    return False


def assert_block_fields(
    env_name: EnvName, response: dict, full_trx: bool, tx_receipt: tp.Optional[types.TxReceipt], pending: bool = False
):
    assert "error" not in response
    assert "result" in response, AssertMessage.DOES_NOT_CONTAIN_RESULT
    result = response["result"]
    expected_hex_fields = [
        "difficulty",
        "gasLimit",
        "gasUsed",
        "hash",
        "logsBloom",
        "miner",
        "mixHash",
        "nonce",
        "number",
        "parentHash",
        "receiptsRoot",
        "sha3Uncles",
        "size",
        "stateRoot",
        "timestamp",
        "transactionsRoot",
    ]
    if pending:
        for i in ["hash", "nonce", "miner"]:
            expected_hex_fields.remove(i)
    for field in expected_hex_fields:
        assert is_hex(result[field]), f"Field {field} must be hex but '{result[field]}'"
    if tx_receipt is not None:
        assert (
            result["hash"] == tx_receipt.blockHash.hex()
        ), f"Actual:{result['hash']}; Expected: {tx_receipt.blockHash.hex()}"

        assert result["number"] == hex(
            tx_receipt.blockNumber
        ), f"Actual:{result['number']}; Expected: {hex(tx_receipt.blockNumber)}"

        assert int(result["gasUsed"], 16) >= int(
            hex(tx_receipt.gasUsed), 16
        ), f"Actual:{result['gasUsed']} or more; Expected: {hex(tx_receipt.gasUsed)}"

        assert result["extraData"].startswith("0x")  # this field's value is optional

        difficulty = result["totalDifficulty"]
        if env_name is EnvName.GETH:
            assert is_hex(difficulty)
        else:
            assert difficulty == "0x0"

    assert result["uncles"] == []
    transactions = result["transactions"]
    if full_trx:
        if tx_receipt is not None:
            assert tx_receipt.transactionHash.hex() in [
                transaction["hash"] for transaction in transactions
            ], "Created transaction should be in block"
        for transaction in transactions:
            expected_hex_fields = [
                "hash",
                "nonce",
                "blockHash",
                "blockNumber",
                "transactionIndex",
                "from",
                "value",
                "gas",
                "gasPrice",
                "v",
                "r",
                "s",
            ]
            for field in expected_hex_fields:
                assert is_hex(transaction[field]), f"field '{field}' is not correct. Actual : {transaction[field]}"
            if tx_receipt is not None:
                if tx_receipt.transactionHash.hex() == transaction["hash"]:
                    assert transaction["from"].upper() == tx_receipt["from"].upper()
                    assert transaction["to"].upper() == tx_receipt["to"].upper()
                    assert transaction["input"] == "0x"
    else:
        for transaction in transactions:
            assert is_hex(transaction)
        if tx_receipt is not None:
            assert tx_receipt.transactionHash.hex() in transactions, "Created transaction should be in block"


def assert_log_field_in_neon_trx_receipt(response, events_count):

    expected_event_types = ["EnterCall"]
    for i in range(events_count):
        expected_event_types.append("Log")
    expected_event_types.append("ExitStop")
    expected_event_types.append("Return")
    all_logs = []

    for trx in response["result"]["solanaTransactions"]:
        expected_int_fields = ["solanaBlockSlot", "solanaLamportExpense"]
        assert_fields_are_specified_type(int, trx, expected_int_fields)

        assert trx["solanaTransactionIsSuccess"] == True
        instructions = trx["solanaInstructions"]
        assert instructions != []
        for instruction in instructions:
            expected_int_fields = [
                "solanaInstructionIndex",
                "svmHeapSizeLimit",
                "svmCyclesLimit",
                "svmCyclesUsed",
                "neonInstructionCode",
                "neonEvmSteps",
                "neonTotalEvmSteps",
                "neonTransactionFee",
                "neonGasUsed",
                "neonTotalGasUsed",
            ]
            assert_fields_are_specified_type(int, instruction, expected_int_fields)
            assert instruction["solanaProgram"] == "NeonEVM"
            assert instruction["solanaInnerInstructionIndex"] is None
            neon_logs = instruction["neonLogs"]
            if instruction["neonInstructionName"] != "HolderWrite":
                assert neon_logs != [], f"Logs shouldn't be empty in {instruction}"
                for log in neon_logs:
                    all_logs.append(log)
                event_types = [log["neonEventType"] for log in sorted(all_logs, key=lambda x: x["neonEventOrder"])]
                assert event_types == expected_event_types, f"Actual: {event_types}; Expected: {expected_event_types}"


def assert_fields_are_hex(obj, expected_hex_fields):
    if isinstance(obj, SimpleNamespace):
        for field in expected_hex_fields:
            assert hasattr(obj, field), f"no expected field {field} in the object"
            assert is_hex(getattr(obj, field)), f"field {field} is not correct. Actual: {getattr(obj, field)}"
        return

    for field in expected_hex_fields:
        assert field in obj, f"no expected field {field} in the object"
        assert is_hex(obj[field]), f"field {field} is not correct. Actual: {obj[field]}"


def assert_fields_are_specified_type(_type: type, obj, expected_type_fields):
    for field in expected_type_fields:
        assert field in obj, f"no expected field {field} in the object"
        t = type(obj[field])
        assert t is _type or NoneType, f"field {field} is not {_type.__name__}. Actual: {t}"


def assert_equal_fields(result, comparable_object, comparable_fields, keys_mappings=None):
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
        if isinstance(r, int):
            r = hex(r)
        if isinstance(r, HexBytes):
            r = r.hex()

        if is_hex(r):
            # Ethereum is case-insensitive to addresses and block hashes
            # Geth sometimes returns the same hash with a few characters in different register (upper or lower)
            l = l.lower()
            r = r.lower()

        assert (
            l.lower() == r.lower()
        ), f"The field '{field}' {l} from response  is not equal to {field} from receipt {r}"


def count_events(
    neon_trx_receipt: NeonGetTransactionResult,
    ignored_events=[NeonEventType.InvalidRevision, NeonEventType.StepReset],
    is_removed=False,
):
    events = neon_trx_receipt.get_all_events(ignore_events=ignored_events, is_removed=is_removed)
    return Counter([event.neonEventType for event in events])


def assert_events_by_type(neon_trx_receipt: NeonGetTransactionResult):
    events = neon_trx_receipt.get_all_events(ignore_events=[NeonEventType.InvalidRevision, NeonEventType.StepReset])
    for event in events:
        match event.neonEventType:
            case NeonEventType.EnterCreate.value:
                assert (
                    event.address is not None
                ), f"Expecting non-empty address for {NeonEventType.EnterCreate}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.EnterCreate}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.EnterCreate}, got {event}"
            case NeonEventType.ExitStop.value:
                if not event.removed:
                    assert (
                        event.address is not None
                    ), f"Expecting non-empty address for {NeonEventType.ExitStop}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.Return}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.Return}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.ExitStop}, got {event}"
            case NeonEventType.Return.value:
                assert event.address is None, f"Expecting empty address for {NeonEventType.Return}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.Return}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.Return}, got {event}"

                assert event.data != "0x", f"Expecting non-empty data for {NeonEventType.Return}, got {event}"

                assert event.neonEventLevel == 0, f"Expecting level 0 for {NeonEventType.Return}, got {event}"
            case NeonEventType.EnterCall.value:
                assert event.address is not None, f"Expecting empty address for {NeonEventType.EnterCall}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.Return}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.Return}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.EnterCall}, got {event}"
            case NeonEventType.Log.value:
                assert event.topics is not None, f"Expecting non-empty topics for {NeonEventType.Log}, got {event}"
                assert isinstance(event.topics, list), f"Expecting list of topics for {NeonEventType.Log}, got {event}"
                assert len(event.topics) > 0, f"Expecting non-empty topics for {NeonEventType.Log}, got {event}"
            case NeonEventType.Cancel.value:
                assert event.address is None, f"Expecting empty address for {NeonEventType.Cancel}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.Cancel}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.Cancel}, got {event}"

                assert event.data == "0x00", f"Expecting empty data for {NeonEventType.Cancel}, got {event}"
            case NeonEventType.EnterCallCode.value:
                assert event.data == "0x", f"Expecting empty data for {NeonEventType.EnterCallCode}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.EnterCallCode}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.EnterCallCode}, got {event}"

                assert event.neonEventLevel == 2, f"Expecting level 2 for {NeonEventType.EnterCallCode}, got {event}"
            case NeonEventType.ExitReturn.value:
                assert event.address is not None, f"Expecting empty address for {NeonEventType.ExitReturn}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.ExitReturn}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.ExitReturn}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.ExitReturn}, got {event}"
            case NeonEventType.EnterStaticCall.value:
                assert (
                    event.address is not None
                ), f"Expecting empty address for {NeonEventType.EnterStaticCall}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.EnterStaticCall}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.EnterStaticCall}, got {event}"
                assert (
                    len(event.topics) == 0
                ), f"Expecting empty topics for {NeonEventType.EnterStaticCall}, got {event}"

                assert event.neonEventLevel == 2, f"Expecting level 2 for {NeonEventType.EnterStaticCall}, got {event}"
            case NeonEventType.EnterDelegateCall.value:
                assert (
                    event.address is not None
                ), f"Expecting empty address for {NeonEventType.EnterDelegateCall}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.EnterDelegateCall}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.EnterDelegateCall}, got {event}"
                assert (
                    len(event.topics) == 0
                ), f"Expecting empty topics for {NeonEventType.EnterDelegateCall}, got {event}"
            case NeonEventType.ExitSendAll.value:
                assert (
                    event.address is not None
                ), f"Expecting empty address for {NeonEventType.ExitSendAll}, got {event}"

                assert event.data == "0x", f"Expecting empty data for {NeonEventType.ExitSendAll}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.ExitSendAll}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.ExitSendAll}, got {event}"
            case NeonEventType.ExitRevert.value:
                assert event.address is not None, f"Expecting empty address for {NeonEventType.ExitRevert}, got {event}"

                assert isinstance(
                    event.topics, list
                ), f"Expecting list of topics for {NeonEventType.ExitRevert}, got {event}"
                assert len(event.topics) == 0, f"Expecting empty topics for {NeonEventType.ExitRevert}, got {event}"
            case _:
                assert event.neonEventType in NeonEventType, "Unknown event type {event_type}"


def assert_events_order(neon_trx_receipt: NeonGetTransactionResult, is_removed=False):
    events = neon_trx_receipt.get_all_events(
        ignore_events=[NeonEventType.InvalidRevision, NeonEventType.StepReset], is_removed=is_removed
    )
    actual_order_idxs = [event.neonEventOrder for event in events]
    assert len(actual_order_idxs) == len(set(actual_order_idxs)), f"Non-unique indexes for events: {events}"


def assert_event_field(
    neon_trx_receipt: NeonGetTransactionResult, event_type, field_name, expected_value, comparator="=="
):
    events = neon_trx_receipt.get_all_events(filter_by_type=event_type)
    assert events, f"No events of type {event_type} found in {neon_trx_receipt}."
    for event in events:
        match comparator:
            case "==":
                assert (
                    getattr(event, field_name) == expected_value
                ), f"Expecting {field_name} to be {expected_value}, got {getattr(event, field_name)}. Event: {event}."
            case "!=":
                assert (
                    getattr(event, field_name) != expected_value
                ), f"Expecting {field_name} to be different from {expected_value}, got {getattr(event, field_name)}. Event: {event}."
            case "is":
                assert (
                    getattr(event, field_name) is expected_value
                ), f"Expecting {field_name} to be {expected_value}, got {getattr(event, field_name)}. Event: {event}."
            case "is not":
                assert (
                    getattr(event, field_name) is not expected_value
                ), f"Expecting {field_name} to be different from {expected_value}, got {getattr(event, field_name)}. Event: {event}."


def assert_instructions(neon_trx_receipt: NeonGetTransactionResult):
    covered_instructions = [
        SolanaInstruction.TxExecFromData,
        SolanaInstruction.TxStepFromData,
        SolanaInstruction.CancelWithHash,
        SolanaInstruction.TxExecFromDataSolanaCall,
        SolanaInstruction.HolderWrite,
        SolanaInstruction.TxExecFromAccountSolanaCall,
        SolanaInstruction.TxStepFromAccountNoChainId,
        SolanaInstruction.TxExecFromAccount,
        SolanaInstruction.TxStepFromAccount,
    ]
    all_instructions = []
    for trx in neon_trx_receipt.result.solanaTransactions:
        all_instructions.extend(trx.solanaInstructions)
    assert len(all_instructions) > 0
    for instruction in all_instructions:
        assert instruction.neonInstructionName in [
            inst.inst_name for inst in covered_instructions
        ], f"Uncovered instruction {instruction.neonInstructionName}"

        assert instruction.neonInstructionCode == SolanaInstruction[instruction.neonInstructionName].inst_code, (
            f"Instruction {instruction.neonInstructionName} has wrong code. "
            f"Expected: {SolanaInstruction[instruction.neonInstructionName].inst_code}, "
            f"got: {instruction.neonInstructionCode}"
        )


def count_instructions(neon_trx_receipt: NeonGetTransactionResult):
    all_instructions = []
    for trx in neon_trx_receipt.result.solanaTransactions:
        all_instructions.extend(trx.solanaInstructions)
    return Counter([instruction.neonInstructionName for instruction in all_instructions])


def assert_solana_trxs_in_neon_receipt(rpc_client, trx_hash, neon_receipt: NeonGetTransactionResult):
    response = rpc_client.get_solana_trx_by_neon(trx_hash)
    solana_transactions = SolanaByNeonTransaction(**response)

    solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in neon_receipt.result.solanaTransactions]
    assert set(solana_transactions.result) == set(solana_trxs_by_neon)
