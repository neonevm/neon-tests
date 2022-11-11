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
            expected_hex_fields = ["hash", "nonce", "blockHash", "blockNumber", "transactionIndex", "from", "to",
                                   "value", "gas", "gasPrice", "v", "r", "s"]
            for field in expected_hex_fields:
                assert is_hex(transaction[field]), f"field '{field}' is not correct. Block : {block}"
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
