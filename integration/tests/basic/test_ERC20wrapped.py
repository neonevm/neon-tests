import random

import allure
import pytest
import web3
from solana.rpc.types import TokenAccountOpts

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import gen_hash_of_block

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
UINT64_LIMIT = 18446744073709551615
MAX_TOKENS_AMOUNT = 1000000000000000

NO_ENOUGH_GAS_PARAMS = [({'gas_price': 0}, "transaction underpriced"),
                        ({'gas': 0}, "gas limit reached")]


@pytest.fixture(scope="function")
def new_account(web3_client, faucet):
    new_acc = web3_client.create_account()
    faucet.request_neon(new_acc.address, 100)
    yield new_acc


@allure.story("Basic: Tests for contract created by createErc20ForSplMintable call")
class TestERC20wrappedContract(BaseMixin):

    @pytest.fixture(scope="function")
    def restore_balance(self, erc20wrapper):
        yield
        default_value = MAX_TOKENS_AMOUNT
        current_balance = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        if current_balance > default_value:
            erc20wrapper.burn(erc20wrapper.account, erc20wrapper.account.address, current_balance - default_value)
        else:
            erc20wrapper.mint_tokens(erc20wrapper.account, erc20wrapper.account.address,
                                     default_value - current_balance)

    def test_balanceOf(self, erc20wrapper):
        transfer_amount = random.randint(0, 100)
        initial_balance = erc20wrapper.contract.functions.balanceOf(self.recipient_account.address).call()
        self.web3_client.send_erc20(erc20wrapper.account, self.recipient_account, transfer_amount,
                                    erc20wrapper.contract.address,
                                    abi=erc20wrapper.contract.abi)
        assert erc20wrapper.contract.functions.balanceOf(
            self.recipient_account.address).call() == initial_balance + transfer_amount

    @pytest.mark.parametrize("address, expected_exception",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress),
                              (gen_hash_of_block(5), web3.exceptions.ValidationError)])
    def test_balanceOf_with_incorrect_address(self, erc20wrapper, address, expected_exception):
        with pytest.raises(expected_exception):
            return erc20wrapper.contract.functions.balanceOf(address).call()

    def test_mint_to_self(self, erc20wrapper, restore_balance):
        balance_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20wrapper.mint_tokens(erc20wrapper.account, erc20wrapper.account.address, amount)
        balance_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        assert balance_after == balance_before + amount

    def test_mint_to_another_account(self, erc20wrapper, new_account):
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20wrapper.mint_tokens(erc20wrapper.account, new_account.address, amount)
        balance_after = erc20wrapper.contract.functions.balanceOf(new_account.address).call()
        assert balance_after == amount

    def test_mint_by_no_minter_role(self, erc20wrapper):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.MUST_HAVE_MINTER_ROLE_ERC20.value):
            erc20wrapper.mint_tokens(self.recipient_account, self.recipient_account.address, 0)

    @pytest.mark.parametrize("address_to, expected_exception, msg",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress,
                               ErrorMessage.INVALID_ADDRESS_ERC20.value),
                              (ZERO_ADDRESS, web3.exceptions.ContractLogicError,
                               str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "mint to"))
                              ])
    def test_mint_with_incorrect_address(self, erc20wrapper, address_to, expected_exception, msg):
        with pytest.raises(expected_exception, match=msg):
            erc20wrapper.mint_tokens(erc20wrapper.account, address_to, 10)

    def test_mint_with_too_big_amount(self, erc20wrapper):
        with pytest.raises(web3.exceptions.ContractLogicError, match='total mint amount exceeds uint64 max'):
            erc20wrapper.mint_tokens(erc20wrapper.account, erc20wrapper.account.address, UINT64_LIMIT)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_mint_no_enough_gas(self, erc20wrapper, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.mint_tokens(erc20wrapper.account, erc20wrapper.account.address, 1, **param)

    def test_totalSupply(self, erc20wrapper):
        total_before = erc20wrapper.contract.functions.totalSupply().call()
        amount = random.randint(0, 10000)
        erc20wrapper.mint_tokens(erc20wrapper.account, erc20wrapper.account.address, amount)
        total_after = erc20wrapper.contract.functions.totalSupply().call()
        assert total_before + amount == total_after, "Total supply is not correct"

    def test_decimals(self, erc20wrapper):
        decimals = erc20wrapper.contract.functions.decimals().call()
        assert decimals == erc20wrapper.decimals

    def test_burn(self, erc20wrapper, restore_balance):
        balance_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        total_before = erc20wrapper.contract.functions.totalSupply().call()
        amount = random.randint(0, balance_before)
        erc20wrapper.burn(erc20wrapper.account, erc20wrapper.account.address, amount)
        balance_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        total_after = erc20wrapper.contract.functions.totalSupply().call()

        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    @pytest.mark.parametrize("address, expected_exception, msg",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress,
                               ErrorMessage.INVALID_ADDRESS_ERC20.value),
                              (gen_hash_of_block(25), web3.exceptions.InvalidAddress,
                               "is invalid"),
                              (ZERO_ADDRESS, web3.exceptions.ContractLogicError,
                               str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "burn from"))
                              ])
    def test_burn_incorrect_address(self, erc20wrapper, address, expected_exception, msg):
        with pytest.raises(expected_exception, match=msg):
            erc20wrapper.burn(erc20wrapper.account, address, 1)

    def test_burn_more_than_total_supply(self, erc20wrapper):
        total = erc20wrapper.contract.functions.totalSupply().call()
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=str.format(ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "burn")):
            erc20wrapper.burn(erc20wrapper.account, erc20wrapper.account.address, total + 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burn_no_enough_gas(self, erc20wrapper, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.burn(erc20wrapper.account, erc20wrapper.account.address, 1, **param)

    def test_burnFrom(self, erc20wrapper, new_account, restore_balance):
        balance_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        total_before = erc20wrapper.contract.functions.totalSupply().call()
        amount = random.randint(0, balance_before)
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        erc20wrapper.burn_from(signer=new_account, from_address=erc20wrapper.account.address, amount=amount)

        balance_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        total_after = erc20wrapper.contract.functions.totalSupply().call()
        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    def test_burnFrom_without_allowance(self, erc20wrapper, new_account):
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value):
            erc20wrapper.burn_from(new_account, erc20wrapper.account.address, 10)

    def test_burnFrom_more_than_allowanced(self, erc20wrapper, new_account):
        amount = 2
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value):
            erc20wrapper.burn_from(new_account, erc20wrapper.account.address, amount + 1)

    def test_burnFrom_incorrect_address(self, erc20wrapper):
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20wrapper.burn_from(erc20wrapper.account, gen_hash_of_block(20), 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burnFrom_no_enough_gas(self, erc20wrapper, new_account, param, msg):
        erc20wrapper.approve(erc20wrapper.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.burn_from(new_account, erc20wrapper.account.address, 1, **param)

    def test_approve_more_than_total_supply(self, erc20wrapper, new_account):
        amount = erc20wrapper.contract.functions.totalSupply().call() + 1
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        allowance = erc20wrapper.contract.functions.allowance(erc20wrapper.account.address, new_account.address).call()
        assert allowance == amount

    @pytest.mark.parametrize("address, expected_exception, msg",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress,
                               ErrorMessage.INVALID_ADDRESS_ERC20.value),
                              (ZERO_ADDRESS, web3.exceptions.ContractLogicError,
                               str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "approve to"))
                              ])
    def test_approve_incorrect_address(self, erc20wrapper, address, expected_exception, msg):
        with pytest.raises(expected_exception, match=msg):
            erc20wrapper.approve(erc20wrapper.account, address, 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_approve_no_enough_gas(self, erc20wrapper, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.approve(erc20wrapper.account, erc20wrapper.account.address, 1, **param)

    def test_allowance_incorrect_address(self, erc20wrapper):
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20wrapper.contract.functions.allowance(erc20wrapper.account.address, gen_hash_of_block(20)).call()

    def test_allowance_for_new_account(self, erc20wrapper, new_account):
        allowance = erc20wrapper.contract.functions.allowance(new_account.address, erc20wrapper.account.address).call()
        assert allowance == 0

    def test_transfer(self, erc20wrapper, new_account, restore_balance):
        balance_acc1_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        balance_acc2_before = erc20wrapper.contract.functions.balanceOf(new_account.address).call()
        total_before = erc20wrapper.contract.functions.totalSupply().call()
        amount = random.randint(1, balance_acc1_before)
        erc20wrapper.transfer(erc20wrapper.account, new_account.address, amount)
        balance_acc1_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        balance_acc2_after = erc20wrapper.contract.functions.balanceOf(new_account.address).call()
        total_after = erc20wrapper.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    @pytest.mark.parametrize("address, expected_exception, msg",
                             [(gen_hash_of_block(20), web3.exceptions.InvalidAddress,
                               ErrorMessage.INVALID_ADDRESS_ERC20.value),
                              (ZERO_ADDRESS, web3.exceptions.ContractLogicError,
                               str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "transfer to"))
                              ])
    def test_transfer_incorrect_address(self, erc20wrapper, address, expected_exception, msg):
        with pytest.raises(expected_exception, match=msg):
            erc20wrapper.transfer(erc20wrapper.account, address, 1)

    def test_transfer_more_than_balance(self, erc20wrapper):
        balance = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=str.format(ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "transfer")):
            erc20wrapper.transfer(erc20wrapper.account, erc20wrapper.account.address, balance + 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transfer_no_enough_gas(self, erc20wrapper, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.transfer(erc20wrapper.account, erc20wrapper.account.address, 1, **param)

    def test_transferFrom(self, erc20wrapper, new_account, restore_balance):
        balance_acc1_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        balance_acc2_before = erc20wrapper.contract.functions.balanceOf(new_account.address).call()
        total_before = erc20wrapper.contract.functions.totalSupply().call()
        amount = random.randint(1, balance_acc1_before)
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        erc20wrapper.transfer_from(new_account, erc20wrapper.account.address, new_account.address, amount)
        balance_acc1_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        balance_acc2_after = erc20wrapper.contract.functions.balanceOf(new_account.address).call()
        total_after = erc20wrapper.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    def test_transferFrom_without_allowance(self, erc20wrapper, new_account):
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value):
            erc20wrapper.transfer_from(signer=new_account, address_from=erc20wrapper.account.address,
                                       address_to=new_account.address, amount=10)

    def test_transferFrom_more_than_allowanced(self, erc20wrapper, new_account):
        amount = 2
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        with pytest.raises(web3.exceptions.ContractLogicError, match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value):
            erc20wrapper.transfer_from(signer=new_account, address_from=erc20wrapper.account.address,
                                       address_to=new_account.address, amount=amount + 1)

    def test_transferFrom_incorrect_address(self, erc20wrapper):
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20wrapper.transfer_from(signer=erc20wrapper.account, address_from=erc20wrapper.account.address,
                                       address_to=gen_hash_of_block(20), amount=1)

    def test_transferFrom_more_than_balance(self, erc20wrapper, new_account):
        amount = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call() + 1
        erc20wrapper.approve(erc20wrapper.account, new_account.address, amount)
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match=str.format(ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "transfer")):
            erc20wrapper.transfer_from(signer=new_account, address_from=erc20wrapper.account.address,
                                       address_to=new_account.address, amount=amount)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transferFrom_no_enough_gas(self, erc20wrapper, new_account, param, msg):
        erc20wrapper.approve(erc20wrapper.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20wrapper.transfer_from(new_account, erc20wrapper.account.address, new_account.address, 1, **param)

    def test_transferSolana(self, erc20wrapper, sol_client, solana_acc):
        acc, token_mint, solana_address = solana_acc
        amount = random.randint(10000, 1000000)
        sol_balance_before = sol_client.get_balance(acc.public_key)["result"]["value"]
        contract_balance_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        opts = TokenAccountOpts(token_mint, encoding="jsonParsed")
        erc20wrapper.transfer_solana(erc20wrapper.account, solana_address, amount)
        self.wait_condition(
            lambda: int(
                sol_client.get_token_accounts_by_owner(acc.public_key, opts)['result']['value'][0]['account']['data'][
                    'parsed']['info']['tokenAmount']['amount']) > 0)

        sol_balance_after = sol_client.get_balance(acc.public_key)["result"]["value"]
        token_data = sol_client.get_token_accounts_by_owner(acc.public_key, opts)["result"]["value"][0]
        token_balance_after = token_data['account']['data']['parsed']['info']['tokenAmount']['amount']
        contract_balance_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()

        assert int(token_balance_after) == amount, 'Token balance for sol account is not correct'
        assert contract_balance_before - contract_balance_after == amount, 'Contract balance is not correct'
        assert sol_balance_after == sol_balance_before, 'Sol balance is changed'

    def test_approveSolana(self, erc20wrapper, sol_client, solana_acc):
        acc, token_mint, solana_address = solana_acc
        amount = random.randint(10000, 1000000)
        opts = TokenAccountOpts(token_mint, encoding="jsonParsed")
        erc20wrapper.approve_solana(erc20wrapper.account, bytes(acc.public_key), amount)
        self.wait_condition(
            lambda: len(sol_client.get_token_accounts_by_delegate(acc.public_key, opts)['result']['value']) > 0)
        token_account = sol_client.get_token_accounts_by_delegate(acc.public_key, opts)['result']['value'][0]['account']
        assert int(token_account['data']['parsed']['info']['delegatedAmount']['amount']) == amount
        assert int(token_account['data']['parsed']['info']['delegatedAmount']['decimals']) == erc20wrapper.decimals


@allure.story("Basic: multiply actions tests for multiplyActionsERC20 contract")
class TestMultiplyActionsForERC20(BaseMixin):

    def make_tx_object(self):
        tx = {"from": self.sender_account.address,
              "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
              "gasPrice": self.web3_client.gas_price()}
        return tx

    def test_mint_transfer_burn(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount - 1)
        burn_amount = random.randint(1, mint_amount - transfer_amount)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferBurn(mint_amount, acc.address, transfer_amount,
                                                             burn_amount) \
            .buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == transfer_amount, "User balance is not correct"
        assert contract_balance == mint_amount - transfer_amount - burn_amount, "Contract balance is not correct"

    def test_mint_transfer_transfer_one_recipient(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferTransfer(mint_amount, acc.address, transfer_amount_1,
                                                                 acc.address, transfer_amount_2) \
            .buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == transfer_amount_1 + transfer_amount_2, "User balance is not correct"
        assert contract_balance == mint_amount - transfer_amount_1 - transfer_amount_2, \
            "Contract balance is not correct"

    def test_mint_transfer_transfer_different_recipients(self, multiply_actions_erc20, new_account):
        acc_1, contract = multiply_actions_erc20
        acc_2 = new_account
        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferTransfer(mint_amount, acc_1.address, transfer_amount_1,
                                                                 acc_2.address, transfer_amount_2) \
            .buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_1_balance = contract.functions.balance(acc_1.address).call()
        user_2_balance = contract.functions.balance(acc_2.address).call()

        assert user_1_balance == transfer_amount_1, "User 1 balance is not correct"
        assert user_2_balance == transfer_amount_2, "User 2 balance is not correct"
        assert contract_balance == mint_amount - transfer_amount_1 - transfer_amount_2, \
            "Contract balance is not correct"

    def test_transfer_mint_burn(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount_1)
        burn_amount = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.transferMintBurn(acc.address, transfer_amount, mint_amount_2,
                                                             burn_amount).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert contract_balance == mint_amount_1 + mint_amount_2 - transfer_amount - burn_amount, \
            "Contract balance is not correct"
        assert user_balance == transfer_amount, "User balance is not correct"

    def test_transfer_mint_transfer_burn(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount_1)
        transfer_amount_2 = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount_1)
        burn_amount = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount_1 - transfer_amount_2)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions. \
            transferMintTransferBurn(acc.address, transfer_amount_1, mint_amount_2, transfer_amount_2,
                                     burn_amount).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert contract_balance == mint_amount_1 + mint_amount_2 - transfer_amount_1 - transfer_amount_2 - burn_amount, \
            "Contract balance is not correct"
        assert user_balance == transfer_amount_1 + transfer_amount_2, "User balance is not correct"

    def test_mint_burn_transfer(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount - 1)
        transfer_amount = mint_amount - burn_amount

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintBurnTransfer(mint_amount, burn_amount, acc.address, transfer_amount, ) \
            .buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert user_balance == transfer_amount, "User balance is not correct"
        assert contract_balance == 0, "Contract balance is not correct"

    def test_burn_transfer_burn_transfer(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount = random.randint(10, 100000000)
        burn_amount_1 = random.randint(1, mint_amount - 2)
        transfer_amount_1 = random.randint(1, mint_amount - burn_amount_1 - 2)
        burn_amount_2 = random.randint(1, mint_amount - burn_amount_1 - transfer_amount_1 - 1)
        transfer_amount_2 = random.randint(1, mint_amount - burn_amount_1 - transfer_amount_1 - burn_amount_2)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions. \
            burnTransferBurnTransfer(burn_amount_1, acc.address, transfer_amount_1, burn_amount_2, acc.address,
                                     transfer_amount_2).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert contract_balance == mint_amount - transfer_amount_1 - transfer_amount_2 - burn_amount_1 - burn_amount_2, \
            "Contract balance is not correct"
        assert user_balance == transfer_amount_1 + transfer_amount_2, "User balance is not correct"

    def test_burn_mint_transfer(self, multiply_actions_erc20):
        acc, contract = multiply_actions_erc20
        mint_amount_1 = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount_1)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(mint_amount_1 - burn_amount, mint_amount_1 - burn_amount + mint_amount_2)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions. \
            burnMintTransfer(burn_amount, mint_amount_2, acc.address, transfer_amount).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert contract_balance == mint_amount_1 + mint_amount_2 - transfer_amount - burn_amount, \
            "Contract balance is not correct"
        assert user_balance == transfer_amount, "User balance is not correct"
