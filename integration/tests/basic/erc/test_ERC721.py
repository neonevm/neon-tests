import datetime

import allure
import base58
import pytest
import web3
import web3.exceptions
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey

from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils import metaplex
from utils.accounts import EthAccounts
from utils.consts import ZERO_ADDRESS
from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.helpers import gen_hash_of_block, generate_text, wait_condition
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


@allure.feature("ERC Verifications")
@allure.story("ERC721: Verify integration with Metaplex")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestERC721:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    @pytest.fixture(scope="function")
    def token_id(self, erc721, web3_client) -> int:
        seed = web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id_ = erc721.mint(seed, erc721.account.address, uri)
        yield token_id_

    @allure.step("Check metaplex data")
    def metaplex_checks(self, token_id: int):
        solana_acc = base58.b58encode(token_id.to_bytes(32, "big")).decode("utf-8")
        metaplex.wait_account_info(self.sol_client, Pubkey.from_string(solana_acc))
        metadata = metaplex.get_metadata(self.sol_client, Pubkey.from_string(solana_acc))
        assert metadata["mint"] == solana_acc.encode("utf-8")
        assert metadata["data"]["name"] == "Metaplex"
        assert metadata["data"]["symbol"] == "MPL"

    def test_mint_with_used_seed(self, erc721, accounts):
        recipient = accounts[1]

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        erc721.mint(seed, erc721.account.address, uri)
        with pytest.raises(web3.exceptions.ContractLogicError, match="invalid owner"):
            erc721.mint(seed, recipient.address, uri)

    def test_name(self, erc721):
        name = erc721.contract.functions.name().call()
        assert name == "Metaplex"

    def test_symbol(self, erc721):
        symbol = erc721.contract.functions.symbol().call()
        assert symbol == "MPL"

    def test_balance_of(self, erc721):
        balance_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        uri = generate_text(min_len=10, max_len=200)

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        erc721.mint(seed, erc721.account.address, uri)

        balance = erc721.contract.functions.balanceOf(erc721.account.address).call()
        assert balance - balance_before == 1

    def test_owner_of(self, erc721, token_id):
        owner = erc721.contract.functions.ownerOf(token_id).call()
        assert owner == erc721.account.address

    def test_token_uri(self, erc721):
        uri = generate_text(min_len=10, max_len=200)
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        token_id = erc721.mint(seed, erc721.account.address, uri)
        token_uri = erc721.contract.functions.tokenURI(token_id).call()
        assert token_uri == uri

    @pytest.mark.cost_report
    def test_transfer_from_with_approval(self, erc721, token_id, accounts):
        recipient = accounts[2]

        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(recipient.address).call()

        erc721.approve(recipient.address, token_id, erc721.account)
        erc721.transfer_from(erc721.account.address, recipient.address, token_id, recipient)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(recipient.address).call()

        assert balance_usr1_after - balance_usr1_before == -1
        assert balance_usr2_after - balance_usr2_before == 1

    def test_safe_transfer_from_with_data(self, erc721, token_id, nft_receiver):
        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(nft_receiver.address).call()
        data = generate_text(max_len=100).encode("utf-8")
        erc721.safe_transfer_from(erc721.account.address, nft_receiver.address, token_id, erc721.account, data)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(nft_receiver.address).call()

        nft_receiver_data = nft_receiver.functions.contractData().call()

        assert nft_receiver_data == data
        assert balance_usr1_after - balance_usr1_before == -1
        assert balance_usr2_after - balance_usr2_before == 1

    def test_safe_transfer_from_to_invalid_contract(self, erc721, token_id, invalid_nft_receiver):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.INVALID_RECEIVER_ERC721.value,
        ):
            erc721.safe_transfer_from(
                erc721.account.address,
                invalid_nft_receiver.address,
                token_id,
                erc721.account,
            )

    def test_set_approval_for_all(self, erc721, accounts):
        recipient = accounts[2]

        tokens = []
        for _ in range(2):
            seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
            uri = generate_text(min_len=10, max_len=200)
            tokens.append(erc721.mint(seed, erc721.account.address, uri))

        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(recipient.address).call()

        erc721.set_approval_for_all(recipient.address, True, erc721.account)
        erc721.transfer_from(erc721.account.address, recipient.address, tokens[0], recipient)

        erc721.set_approval_for_all(recipient.address, False, erc721.account)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.NOT_TOKEN_OWNER_ERC721.value,
        ):
            erc721.transfer_from(erc721.account.address, recipient.address, tokens[1], recipient)
        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(recipient.address).call()

        assert balance_usr1_before - balance_usr1_after == 1
        assert balance_usr2_before - balance_usr2_after == -1

    def test_transfer_solana_from(self, erc721, token_id, solana_account):
        token_mint = Pubkey(token_id.to_bytes(32, "big"))
        ata = self.sol_client.create_associate_token_acc(solana_account, solana_account, token_mint)

        erc721.transfer_solana_from(erc721.account.address, bytes(ata), token_id, erc721.account)
        acc_balance = self.sol_client.get_token_account_balance(ata, commitment=Confirmed).value

        assert int(acc_balance.amount) == 1
        assert int(acc_balance.decimals) == 0


@allure.feature("ERC Verifications")
@allure.story("ERC721: Tests for multiple actions in one transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestMultipleActionsForERC721:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_mint_transfer(self, multiple_actions_erc721):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)

        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintTransfer(seed, uri, acc.address).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == user_balance_before + 1, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    def test_mint_mint_transfer_transfer(self, multiple_actions_erc721):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721

        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.web3_client.make_raw_tx(sender_account)
        seed_1 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        seed_2 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        uri_1 = generate_text(min_len=10, max_len=200)
        uri_2 = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mintMintTransferTransfer(
            seed_1, uri_1, seed_2, uri_2, acc.address, acc.address
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == user_balance_before + 2, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    def test_mint_mint_transfer_transfer_different_accounts(self, multiple_actions_erc721):
        recipient = self.accounts[1]

        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721

        contract_balance_before = contract.functions.contractBalance().call()
        user_1_balance_before = contract.functions.balance(acc.address).call()
        user_2_balance_before = contract.functions.balance(recipient.address).call()

        tx = self.web3_client.make_raw_tx(sender_account)
        seed_1 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        seed_2 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        uri_1 = generate_text(min_len=10, max_len=200)
        uri_2 = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mintMintTransferTransfer(
            seed_1, uri_1, seed_2, uri_2, acc.address, recipient.address
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_1_balance = contract.functions.balance(acc.address).call()
        user_2_balance = contract.functions.balance(recipient.address).call()

        assert user_1_balance == user_1_balance_before + 1, "User 1 balance is not correct"
        assert user_2_balance == user_2_balance_before + 1, "User 2 balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"


@allure.feature("ERC Verifications")
@allure.story("ERC721: Verify extensions")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestERC721Extensions:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_erc_4907_rental_nft(self, faucet):
        recipient_account = self.accounts[1]
        erc4907 = ERC721ForMetaplex(
            self.web3_client,
            faucet,
            contract="EIPs/ERC721/extensions/ERC4907",
            contract_name="ERC4907",
        )

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc4907.mint(seed, erc4907.account.address, uri)
        tx = self.web3_client.make_raw_tx(erc4907.account)

        expires = datetime.datetime.now() + datetime.timedelta(seconds=25)
        expires = int(expires.timestamp())

        instr = erc4907.contract.functions.setUser(token_id, recipient_account.address, expires).build_transaction(tx)
        self.web3_client.send_transaction(erc4907.account, instr)
        assert erc4907.contract.functions.userOf(token_id).call() == recipient_account.address
        assert erc4907.contract.functions.ownerOf(token_id).call() == erc4907.account.address
        wait_condition(
            lambda: erc4907.contract.functions.userOf(token_id).call() == ZERO_ADDRESS, timeout_sec=30, delay=2
        )

    def test_erc_2981_default_royalty(self, faucet):
        recipient_account = self.accounts[1]
        erc2981 = ERC721ForMetaplex(
            self.web3_client,
            faucet,
            contract="EIPs/ERC721/extensions/ERC2981",
            contract_name="ERC721Royalty",
        )

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc2981.mint(seed, erc2981.account.address, uri)
        tx = self.web3_client.make_raw_tx(erc2981.account)
        default_royalty = 15
        sale_price = 10000

        instr = erc2981.contract.functions.setDefaultRoyalty(
            recipient_account.address, default_royalty
        ).build_transaction(tx)
        self.web3_client.send_transaction(erc2981.account, instr)

        info = erc2981.contract.functions.royaltyInfo(token_id, sale_price).call()
        assert info[0] == recipient_account.address
        assert info[1] == default_royalty

    def test_erc_2981_token_royalty(self, faucet):
        recipient_account = self.accounts[1]
        erc2981 = ERC721ForMetaplex(
            self.web3_client,
            faucet,
            contract="EIPs/ERC721/extensions/ERC2981",
            contract_name="ERC721Royalty",
        )

        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc2981.mint(seed, erc2981.account.address, uri)
        tx = self.web3_client.make_raw_tx(erc2981.account)
        default_royalty = 15
        sale_price = 10000

        royalty = 10
        instr = erc2981.contract.functions.setTokenRoyalty(
            token_id, recipient_account.address, royalty
        ).build_transaction(tx)
        self.web3_client.send_transaction(erc2981.account, instr)
        tx = self.web3_client.make_raw_tx(erc2981.account)
        instr = erc2981.contract.functions.setDefaultRoyalty(
            recipient_account.address, default_royalty
        ).build_transaction(tx)
        self.web3_client.send_transaction(erc2981.account, instr)
        info = erc2981.contract.functions.royaltyInfo(token_id, sale_price).call()
        assert info[0] == recipient_account.address
        assert info[1] == royalty
