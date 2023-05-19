import datetime
import time

import allure

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_ADDRESS
from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.helpers import generate_text, gen_hash_of_block


@allure.feature("ERC Verifications")
@allure.story("ERC721: Verify extensions")
class TestERC721Extensions(BaseMixin):

    def test_ERC4907_rental_nft(self, web3_client, faucet):
        erc4907 = ERC721ForMetaplex(web3_client, faucet,
                                    contract="ERC721/extensions/ERC4907",
                                    contract_name="ERC4907")

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc4907.mint(seed, erc4907.account.address, uri)
        tx = self.create_contract_call_tx_object(erc4907.account)

        expires = datetime.datetime.now() + datetime.timedelta(seconds=30)
        expires = int(expires.timestamp())

        instr = erc4907.contract.functions.setUser(token_id, self.recipient_account.address, expires).build_transaction(
            tx)
        self.web3_client.send_transaction(erc4907.account, instr)
        assert erc4907.contract.functions.userOf(token_id).call() == self.recipient_account.address
        assert erc4907.contract.functions.ownerOf(token_id).call() == erc4907.account.address
        time.sleep(30)  # wait for expiration
        assert erc4907.contract.functions.userOf(token_id).call() == ZERO_ADDRESS

    def test_ERC2981_default_royalty(self, web3_client, faucet):
        erc2981 = ERC721ForMetaplex(web3_client, faucet,
                                    contract="ERC721/extensions/ERC2981",
                                    contract_name="ERC721Royalty")

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc2981.mint(seed, erc2981.account.address, uri)
        tx = self.create_contract_call_tx_object(erc2981.account)
        default_royalty = 15
        sale_price = 10000

        instr = erc2981.contract.functions.setDefaultRoyalty(self.recipient_account.address,
                                                             default_royalty).build_transaction(
            tx)
        self.web3_client.send_transaction(erc2981.account, instr)

        info = erc2981.contract.functions.royaltyInfo(token_id, sale_price).call()
        assert info[0] == self.recipient_account.address
        assert info[1] == default_royalty

    def test_ERC2981_token_royalty(self, web3_client, faucet):
        erc2981 = ERC721ForMetaplex(web3_client, faucet,
                                    contract="ERC721/extensions/ERC2981",
                                    contract_name="ERC721Royalty")

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc2981.mint(seed, erc2981.account.address, uri)
        tx = self.create_contract_call_tx_object(erc2981.account)
        default_royalty = 15
        sale_price = 10000

        royalty = 10
        instr = erc2981.contract.functions.setTokenRoyalty(token_id, self.recipient_account.address,
                                                           royalty).build_transaction(
            tx)
        self.web3_client.send_transaction(erc2981.account, instr)
        tx = self.create_contract_call_tx_object(erc2981.account)
        instr = erc2981.contract.functions.setDefaultRoyalty(self.recipient_account.address,
                                                             default_royalty).build_transaction(
            tx)
        self.web3_client.send_transaction(erc2981.account, instr)
        info = erc2981.contract.functions.royaltyInfo(token_id, sale_price).call()
        assert info[0] == self.recipient_account.address
        assert info[1] == royalty
