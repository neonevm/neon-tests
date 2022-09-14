import typing as tp
import web3

from integration.tests.basic.helpers.assert_message import AssertMessage


def is_hex(hex_data: str) -> bool:
    try:
        int(hex_data, 16)
        return True
    except (ValueError, TypeError):
        return False


def assert_block_fields(block: dict, full_trx: bool, tx_receipt: tp.Optional[web3.types.TxReceipt]):
    assert "error" not in block
    assert "result" in block, AssertMessage.DOES_NOT_CONTAIN_RESULT
    result = block["result"]
    expected_hex_fields = ["difficulty", "extraData", "gasLimit", "gasUsed", "hash", "logsBloom", "miner",
                           "mixHash", "nonce", "number", "parentHash", "receiptsRoot", "sha3Uncles", "size",
                           "stateRoot", "timestamp", "totalDifficulty", "transactionsRoot"]
    for field in expected_hex_fields:
        assert is_hex(result[field])
    if tx_receipt is not None:
        assert result["hash"] == tx_receipt.blockHash.hex()
        assert result["number"] == hex(tx_receipt.blockNumber)
        assert result["gasUsed"] == hex(tx_receipt.gasUsed)
    assert result["uncles"] == []
    if len(result["transactions"]) > 0:
        transaction = result["transactions"][0]
        if full_trx:
            expected_hex_fields = ["hash", "nonce", "blockHash", "blockNumber", "transactionIndex", "from", "to",
                                   "value", "gas", "gasPrice", "v", "r", "s"]
            for field in expected_hex_fields:
                assert is_hex(transaction[field])
            if tx_receipt is not None:
                assert transaction["hash"] == tx_receipt.transactionHash.hex()
                assert transaction["from"].upper() == tx_receipt['from'].upper()
                assert transaction["to"].upper() == tx_receipt['to'].upper()
                # FIXME: fix next assert if input field should have hex value
                assert transaction["input"] == '0x'
        else:
            assert is_hex(transaction)
            if tx_receipt is not None:
                assert transaction == tx_receipt.transactionHash.hex()
