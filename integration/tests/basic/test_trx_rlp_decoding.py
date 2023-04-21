import allure

import pytest
import rlp

from hexbytes import HexBytes
from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import Unit


@allure.feature("Ethereum compatibility")
@allure.story("Verify RLP decoding with invalid values")
class TestTrxRlpDecoding(BaseMixin):
    def modify_raw_trx(self, signed_tx, new_v=None, new_r=None, new_s=None):
        decoded_tx = rlp.decode(signed_tx.rawTransaction)
        if new_s is not None:
            decoded_tx[-1] = new_s
        if new_r is not None:
            decoded_tx[-2] = new_r
        if new_v is not None:
            decoded_tx[-3] = new_v

        return HexBytes(rlp.encode(decoded_tx))

    @pytest.fixture(scope="class")
    def signed_tx(self, web3_client):
        acc = web3_client.create_account()
        transaction = {
            "from": acc.address,
            "to": acc.address,
            "value": web3_client.to_wei(2, Unit.ETHER),
            "chainId": web3_client._chain_id,
            "gasPrice": web3_client.gas_price(),
            "gas": 0,
            "nonce": web3_client.eth.get_transaction_count(acc.address),
        }

        signed_tx = web3_client.eth.account.sign_transaction(
            transaction, acc.key
        )
        return signed_tx

    @pytest.mark.parametrize("new_v, expected_error", [(999, "wrong chain id"),
                                                       (0, "insufficient funds for transfer"),
                                                       (1, "Invalid V value 1")])
    def test_modify_v(self, signed_tx, new_v, expected_error):

        new_raw_tx = self.modify_raw_trx(signed_tx, new_v=new_v)
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [new_raw_tx.hex()]
        )
        assert expected_error in response["error"]["message"]

    @pytest.mark.parametrize("new_s, expected_error", [
        (13237258775825350966557245051891674271982401474769237400875435660443279001850,
         "insufficient funds for transfer"),
        (123, "insufficient funds for transfer"),
        ('', "Invalid signature values")])
    def test_modify_s(self, signed_tx, new_s, expected_error):
        new_raw_tx = self.modify_raw_trx(signed_tx,
                                         new_s=new_s)
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [new_raw_tx.hex()]
        )
        assert expected_error in response["error"]["message"]

    @pytest.mark.parametrize("new_r, expected_error", [
        (13237258775825350966557245051891674271982401474769237400875435660443279001850,
         "failed to recover ECDSA public key"),
        (123, "insufficient funds for transfer"),
        ('', "Invalid signature values")])
    def test_modify_r(self, signed_tx, new_r, expected_error):
        new_raw_tx = self.modify_raw_trx(signed_tx, new_r=new_r)
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [new_raw_tx.hex()]
        )
        assert expected_error in response["error"]["message"]

    @pytest.mark.parametrize("index", [6, 10])
    def test_add_waste_to_trx(self, signed_tx, index):
        decoded_tx = rlp.decode(signed_tx.rawTransaction)
        decoded_tx.insert(index, HexBytes(b'\x19p\x16l\xc0'))
        new_trx = HexBytes(rlp.encode(decoded_tx))
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [new_trx.hex()]
        )
        assert "wrong transaction format" in response["error"]["message"]

    def test_add_waste_to_trx_without_decoding(self, signed_tx):
        new_trx = signed_tx.rawTransaction + HexBytes(b'\x19p\x16l\xc0')
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [new_trx.hex()]
        )
        assert "wrong transaction format" in response["error"]["message"]