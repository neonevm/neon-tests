import allure
import pytest
from solana.keypair import Keypair

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client

NAME = "Metaplex"
SYMBOL = "MPX"
URI = "uri"


@allure.feature("EVM tests")
@allure.story("Verify precompiled metaplex contract")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestPrecompiledMetaplex:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def mint_id(self, web3_client, class_account, metaplex_caller):
        mint = Keypair.generate()
        tx = {
            "from": class_account.address,
            "nonce": web3_client.eth.get_transaction_count(class_account.address),
            "gasPrice": web3_client.gas_price(),
        }
        instruction_tx = metaplex_caller.functions.callCreateMetadata(
            bytes(mint.public_key), NAME, SYMBOL, URI
        ).build_transaction(tx)
        resp = web3_client.send_transaction(class_account, instruction_tx)
        log = metaplex_caller.events.LogBytes().process_receipt(resp)[0]
        mint = log["args"]["value"]
        return mint

    def test_create_metadata(self, metaplex):
        sender_account = self.accounts[0]
        mint = Keypair.generate()
        tx = self.web3_client._make_tx_object(sender_account)
        instruction_tx = metaplex.functions.createMetadata(bytes(mint.public_key), NAME, SYMBOL, URI).build_transaction(
            tx
        )

        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_create_master_edition(self, metaplex):
        sender_account = self.accounts[0]
        mint = Keypair.generate()
        tx = self.web3_client._make_tx_object(sender_account)
        instruction_tx = metaplex.functions.createMasterEdition(bytes(mint.public_key), 0).build_transaction(tx)

        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.parametrize(
        "fn_name,expected",
        [("name", NAME), ("symbol", SYMBOL), ("uri", URI), ("isInitialized", True), ("isNFT", False)],
    )
    def test_contract_functions(self, mint_id, metaplex_caller, fn_name, expected):
        assert metaplex_caller.get_function_by_name(fn_name)(mint_id).call() == expected
