import pytest
from solana.keypair import Keypair

from integration.tests.basic.helpers.basic import BaseMixin

NAME = "Metaplex"
SYMBOL = "MPX"
URI = "uri"


class TestPrecompiledMetaplex(BaseMixin):

    @pytest.fixture(scope="class")
    def mint_id(self, web3_client, class_account, metaplex_caller):
        mint = Keypair.generate()
        tx = {
            "from": class_account.address,
            "nonce": web3_client.eth.get_transaction_count(
                class_account.address
            ),
            "gasPrice": web3_client.gas_price(),
        }
        instruction_tx = metaplex_caller.functions.callCreateMetadata(
            bytes(mint.public_key), NAME, SYMBOL, URI) \
            .build_transaction(tx)
        resp = web3_client.send_transaction(class_account, instruction_tx)
        log = metaplex_caller.events.LogBytes().process_receipt(resp)[0]
        mint = log["args"]["value"]
        return mint

    def test_create_metadata(self, metaplex):
        mint = Keypair.generate()
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = metaplex.functions.createMetadata(
            bytes(mint.public_key), NAME, SYMBOL, URI
        ).build_transaction(tx)

        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_create_master_edition(self, metaplex):
        mint = Keypair.generate()
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = metaplex.functions.createMasterEdition(
            bytes(mint.public_key), 0
        ).build_transaction(tx)

        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.parametrize("fn_name,expected", [("name", NAME),
                                                  ("symbol", SYMBOL),
                                                  ("uri", URI),
                                                  ("isInitialized", True),
                                                  ("isNFT", False)])
    def test_contract_functions(self, mint_id, metaplex_caller, fn_name, expected):
        assert metaplex_caller.get_function_by_name(fn_name)(mint_id).call() == expected
