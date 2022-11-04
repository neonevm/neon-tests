import random
import allure
import base58
import pytest
import web3
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account, get_associated_token_address

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin
from utils import metaplex
from utils.helpers import gen_hash_of_block, generate_text

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'

INCORRECT_ADDRESS_PARAMS = ("address, expected_exception",
                            [(gen_hash_of_block(20), web3.exceptions.InvalidAddress),
                             (gen_hash_of_block(5), web3.exceptions.ValidationError)])

NOT_ENOUGH_GAS_PARAMS = ("param, msg", [({'gas_price': 0}, "transaction underpriced"),
                                        ({'gas': 0}, "gas limit reached")])


@allure.story("Basic: Tests for ERC721ForMetaplex")
class TestERC721(BaseMixin):

    @pytest.fixture(scope="function")
    def token_id(self, erc721):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc721.mint(seed, erc721.account.address, uri)
        yield token_id

    @allure.step("Check metaplex data")
    def metaplex_checks(self, token_id):
        solana_acc = base58.b58encode(token_id.to_bytes(32, "big")).decode("utf-8")
        metaplex.wait_account_info(self.sol_client, solana_acc)
        metadata = metaplex.get_metadata(self.sol_client, solana_acc)
        assert metadata['mint'] == solana_acc.encode("utf-8")
        assert metadata["data"]["name"] == "Metaplex"
        assert metadata["data"]["symbol"] == "MPL"
        assert metadata["is_mutable"] is False

    def test_mint(self, erc721):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc721.mint(seed, erc721.account.address, uri)
        self.metaplex_checks(token_id)

    def test_mint_with_used_seed(self, erc721, new_account):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        erc721.mint(seed, erc721.account.address, uri)
        with pytest.raises(web3.exceptions.ContractLogicError):
            erc721.mint(seed, new_account.address, uri)

    def test_mint_can_all(self, erc721, new_account):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        erc721.mint(seed, new_account.address, uri, signer=new_account)

    @pytest.mark.parametrize("address_to, expected_exception, msg",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress,
                               ErrorMessage.INVALID_ADDRESS.value),
                              (ZERO_ADDRESS, web3.exceptions.ContractLogicError,
                               str.format(ErrorMessage.ZERO_ACCOUNT_ERC721.value, "mint to"))
                              ])
    def test_mint_incorrect_address(self, erc721, address_to, expected_exception, msg):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200, simple=True)
        with pytest.raises(expected_exception, match=msg):
            erc721.mint(seed, address_to, uri)

    @pytest.mark.parametrize(*NOT_ENOUGH_GAS_PARAMS)
    def test_mint_no_enough_gas(self, erc721, param, msg):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200, simple=True)
        with pytest.raises(ValueError, match=msg):
            erc721.mint(seed, erc721.account.address, uri, **param)

    def test_name(self, erc721):
        name = erc721.contract.functions.name().call()
        assert name == 'Metaplex'

    def test_symbol(self, erc721):
        symbol = erc721.contract.functions.symbol().call()
        assert symbol == 'MPL'

    def test_balanceOf(self, erc721):
        balance_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        uri = generate_text(min_len=10, max_len=200)
        mint_amount = random.randint(1, 5)
        for _ in range(mint_amount):
            seed = gen_hash_of_block(32)
            erc721.mint(seed, erc721.account.address, uri)

        balance = erc721.contract.functions.balanceOf(erc721.account.address).call()
        assert mint_amount == balance - balance_before

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_balanceOf_incorrect_address(self, erc721, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.contract.functions.balanceOf(address).call()

    def test_ownerOf(self, erc721, token_id):
        owner = erc721.contract.functions.ownerOf(token_id).call()
        assert owner == erc721.account.address

    def test_ownerOf_incorrect_token(self, erc721):
        token_id = random.randint(0, 99999999999)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_TOKEN_ERC721.value):
            erc721.contract.functions.ownerOf(token_id).call()

    def test_tokenURI(self, erc721):
        uri = generate_text(min_len=10, max_len=200)
        seed = gen_hash_of_block(32)
        token_id = erc721.mint(seed, erc721.account.address, uri)
        token_uri = erc721.contract.functions.tokenURI(token_id).call()
        assert token_uri == uri

    def test_tokenURI_incorrect_token(self, erc721):
        token_id = random.randint(0, 99999999999)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_TOKEN_ERC721.value):
            erc721.contract.functions.tokenURI(token_id).call()

    def test_transferFrom(self, erc721, new_account, token_id):
        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(new_account.address).call()

        erc721.transfer_from(erc721.account.address, new_account.address, token_id, erc721.account)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(new_account.address).call()

        assert balance_usr1_after - balance_usr1_before == -1
        assert balance_usr2_after - balance_usr2_before == 1

    def test_transferFrom_not_token_owner(self, erc721, new_account, token_id):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.NOT_TOKEN_OWNER_ERC721.value):
            erc721.transfer_from(erc721.account.address, new_account.address, token_id, new_account)

    def test_transferFrom_incorrect_owner(self, erc721, new_account, token_id):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INCORRECT_OWNER_ERC721.value):
            erc721.transfer_from(new_account.address, erc721.account.address, token_id, erc721.account)

    def test_transferFrom_incorrect_token(self, erc721):
        token_id = random.randint(0, 99999999999)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_TOKEN_ERC721.value):
            erc721.transfer_from(erc721.account.address, erc721.account.address, token_id, erc721.account)

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_transferFrom_incorrect_address_from(self, erc721, token_id, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.transfer_from(address, erc721.account.address, token_id, erc721.account)

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_transferFrom_incorrect_address_to(self, erc721, token_id, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.transfer_from(erc721.account.address, address, token_id, erc721.account)

    @pytest.mark.parametrize(*NOT_ENOUGH_GAS_PARAMS)
    def test_transferFrom_no_enough_gas(self, erc721, token_id, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc721.transfer_from(erc721.account.address, erc721.account.address, token_id, erc721.account, **param)

    def test_transferFrom_with_approval(self, erc721, new_account, token_id):
        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(new_account.address).call()

        erc721.approve(new_account.address, token_id, erc721.account)
        erc721.transfer_from(erc721.account.address, new_account.address, token_id, new_account)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(new_account.address).call()

        assert balance_usr1_after - balance_usr1_before == -1
        assert balance_usr2_after - balance_usr2_before == 1

    def test_approve_for_owner(self, erc721, token_id):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.APPROVAL_TO_OWNER_ERC721.value):
            erc721.approve(erc721.account.address, token_id, erc721.account)

    def test_approve_incorrect_token(self, erc721):
        token_id = random.randint(0, 99999999999)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_TOKEN_ERC721.value):
            erc721.approve(erc721.account.address, token_id, erc721.account)

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_approve_incorrect_address(self, erc721, token_id, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.approve(address, token_id, erc721.account)

    def test_approve_no_owner(self, erc721, token_id, new_account):
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=ErrorMessage.APPROVE_CALLER_IS_NOT_OWNER_ERC721.value):
            erc721.approve(new_account.address, token_id, new_account)

    @pytest.mark.parametrize(*NOT_ENOUGH_GAS_PARAMS)
    def test_approve_no_enough_gas(self, erc721, token_id, new_account, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc721.approve(new_account.address, token_id, erc721.account, **param)

    def test_safeTransferFrom_to_user(self, erc721, token_id, new_account):
        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(new_account.address).call()

        erc721.safe_transfer_from(erc721.account.address, new_account.address, token_id, erc721.account)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(new_account.address).call()

        assert balance_usr1_after - balance_usr1_before == -1
        assert balance_usr2_after - balance_usr2_before == 1

    def test_safeTransferFrom_to_contract(self, erc721, token_id, nft_receiver):
        balance_usr_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_contract_before = erc721.contract.functions.balanceOf(nft_receiver.address).call()

        erc721.safe_transfer_from(erc721.account.address, nft_receiver.address, token_id, erc721.account)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_contract_after = erc721.contract.functions.balanceOf(nft_receiver.address).call()

        assert balance_usr1_after - balance_usr_before == -1
        assert balance_contract_after - balance_contract_before == 1

    def test_safeTransferFrom_with_data(self, erc721, token_id, nft_receiver):
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

    def test_safeTransferFrom_to_invalid_contract(self, erc721, token_id, invalid_nft_receiver):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_RECEIVER_ERC721.value):
            erc721.safe_transfer_from(erc721.account.address, invalid_nft_receiver.address, token_id, erc721.account)

    def test_safeMint_to_user(self, erc721):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc721.safe_mint(seed, erc721.account.address, uri)
        self.metaplex_checks(token_id)

    def test_safeMint_to_contract(self, erc721, nft_receiver):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        token_id = erc721.safe_mint(seed, nft_receiver.address, uri)
        self.metaplex_checks(token_id)

    def test_safeMint_with_data(self, erc721, nft_receiver):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        data = generate_text(max_len=100).encode("utf-8")

        token_id = erc721.safe_mint(seed, nft_receiver.address, uri, data)
        self.metaplex_checks(token_id)

        nft_receiver_data = nft_receiver.functions.contractData().call()
        assert nft_receiver_data == data

    def test_safeMint_to_invalid_contract(self, erc721, invalid_nft_receiver):
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_RECEIVER_ERC721.value):
            erc721.safe_mint(seed, invalid_nft_receiver.address, uri)

    def test_setApprovalForAll(self, erc721, new_account):
        tokens = []
        for _ in range(2):
            seed = gen_hash_of_block(32)
            uri = generate_text(min_len=10, max_len=200)
            tokens.append(erc721.mint(seed, erc721.account.address, uri))

        balance_usr1_before = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_before = erc721.contract.functions.balanceOf(new_account.address).call()

        erc721.set_approval_for_all(new_account.address, True, erc721.account)
        erc721.transfer_from(erc721.account.address, new_account.address, tokens[0], new_account)

        erc721.set_approval_for_all(new_account.address, False, erc721.account)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.NOT_TOKEN_OWNER_ERC721.value):
            erc721.transfer_from(erc721.account.address, new_account.address, tokens[1], new_account)

        balance_usr1_after = erc721.contract.functions.balanceOf(erc721.account.address).call()
        balance_usr2_after = erc721.contract.functions.balanceOf(new_account.address).call()

        assert balance_usr1_before - balance_usr1_after == 1
        assert balance_usr2_before - balance_usr2_after == -1

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_setApprovalForAll_incorrect_address(self, erc721, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.set_approval_for_all(address, True, erc721.account)

    def test_setApprovalForAll_approve_to_caller(self, erc721, token_id):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.APPROVE_TO_CALLER_ERC721.value):
            erc721.set_approval_for_all(erc721.account.address, True, erc721.account)

    @pytest.mark.parametrize(*NOT_ENOUGH_GAS_PARAMS)
    def test_setApprovalForAll_no_enough_gas(self, erc721, token_id, new_account, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc721.set_approval_for_all(new_account.address, True, erc721.account, **param)

    def test_isApprovedForAll(self, erc721, token_id, new_account):
        erc721.set_approval_for_all(new_account.address, True, erc721.account)
        is_approved = erc721.contract.functions.isApprovedForAll(erc721.account.address, new_account.address).call()
        assert is_approved
        erc721.set_approval_for_all(new_account.address, False, erc721.account)
        is_approved = erc721.contract.functions.isApprovedForAll(erc721.account.address, new_account.address).call()
        assert not is_approved

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_isApprovedForAll_incorrect_owner_address(self, erc721, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.contract.functions.isApprovedForAll(address, erc721.account.address).call()

    @pytest.mark.parametrize(*INCORRECT_ADDRESS_PARAMS)
    def test_isApprovedForAll_incorrect_operator_address(self, erc721, address, expected_exception):
        with pytest.raises(expected_exception):
            erc721.contract.functions.isApprovedForAll(erc721.account.address, address).call()

    def test_getApproved(self, erc721, token_id, new_account):
        erc721.approve(new_account.address, token_id, erc721.account)
        approved_acc = erc721.contract.functions.getApproved(token_id).call()
        assert approved_acc == new_account.address

    def test_getApproved_incorrect_token(self, erc721):
        token_id = random.randint(0, 99999999999)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INVALID_TOKEN_ERC721.value):
            erc721.contract.functions.getApproved(token_id).call()

    def test_transferSolanaFrom(self, erc721, token_id, sol_client):
        acc = Keypair.generate()
        sol_client.request_airdrop(acc.public_key, 1000000000)
        self.wait_condition(lambda: sol_client.get_balance(acc.public_key).value == 1000000000)
        token_mint = PublicKey(base58.b58encode(token_id.to_bytes(32, "big")).decode("utf-8"))
        trx = Transaction()
        trx.add(create_associated_token_account(acc.public_key, acc.public_key, token_mint))
        opts = TxOpts(skip_preflight=False, skip_confirmation=False)
        sol_client.send_transaction(trx, acc, opts=opts)
        solana_address = bytes(get_associated_token_address(acc.public_key, token_mint))

        erc721.transfer_solana_from(erc721.account.address, solana_address, token_id, erc721.account)
        opts = TokenAccountOpts(token_mint)

        self.wait_condition(
            lambda: int(
                sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0].account.data.parsed["info"]["tokenAmount"]["amount"]) > 0)
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0]
        token_amount = token_data.account.data.parsed['info']['tokenAmount']
        assert int(token_amount['amount']) == 1
        assert int(token_amount['decimals']) == 0


@allure.story("Basic: multiple actions tests for multipleActionsERC721 contract")
class TestMultipleActionsForERC721(BaseMixin):
    def make_tx_object(self):
        tx = {"from": self.sender_account.address,
              "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
              "gasPrice": self.web3_client.gas_price()}
        return tx

    def test_mint_transfer(self, multiple_actions_erc721):
        acc, contract = multiple_actions_erc721
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)

        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransfer(seed, uri, acc.address).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == user_balance_before + 1, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    def test_transfer_mint(self, multiple_actions_erc721):
        acc, contract = multiple_actions_erc721

        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.make_tx_object()
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mint(seed, uri).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)
        token_id = contract.functions.lastTokenId().call()

        tx = self.make_tx_object()
        seed = gen_hash_of_block(32)
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.transferMint(acc.address, seed, token_id, uri).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == user_balance_before + 1, "User balance is not correct"
        assert contract_balance == contract_balance_before + 1, "Contract balance is not correct"

    @pytest.mark.xfail(reason="NDEV-700")
    def test_mint_mint_transfer_transfer(self, multiple_actions_erc721):
        acc, contract = multiple_actions_erc721

        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.make_tx_object()
        seed_1 = gen_hash_of_block(32)
        seed_2 = gen_hash_of_block(32)
        uri_1 = generate_text(min_len=10, max_len=200)
        uri_2 = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mintMintTransferTransfer(seed_1, uri_1, seed_2, uri_2, acc.address,
                                                                     acc.address).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == user_balance_before + 2, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    @pytest.mark.xfail(reason="NDEV-700")
    def test_mint_mint_transfer_transfer_different_accounts(self, multiple_actions_erc721, new_account):
        acc, contract = multiple_actions_erc721

        contract_balance_before = contract.functions.contractBalance().call()
        user_1_balance_before = contract.functions.balance(acc.address).call()
        user_2_balance_before = contract.functions.balance(new_account.address).call()

        tx = self.make_tx_object()
        seed_1 = gen_hash_of_block(32)
        seed_2 = gen_hash_of_block(32)
        uri_1 = generate_text(min_len=10, max_len=200)
        uri_2 = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mintMintTransferTransfer(seed_1, uri_1, seed_2, uri_2, acc.address,
                                                                     new_account.address).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_1_balance = contract.functions.balance(acc.address).call()
        user_2_balance = contract.functions.balance(new_account.address).call()

        assert user_1_balance == user_1_balance_before + 1, "User 1 balance is not correct"
        assert user_2_balance == user_2_balance_before + 1, "User 2 balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"
