import random

import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import gen_hash_of_block


@allure.story("Basic: Tests for contract created by createErc20ForSplMintable call")
class TestERC20wrappedContract(BaseMixin):

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
                              (gen_hash_of_block(5), web3.exceptions.ValidationError),
                              ("", web3.exceptions.ValidationError)])
    def test_balanceOf_with_incorrect_address(self, erc20wrapper, address, expected_exception):
        with pytest.raises(expected_exception):
            return erc20wrapper.contract.functions.balanceOf(address).call()

    def test_mint(self, erc20wrapper):
        balance_before = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        amount = random.randint(1, 1000000000000000)
        erc20wrapper.mint_tokens(erc20wrapper.account, amount)
        balance_after = erc20wrapper.contract.functions.balanceOf(erc20wrapper.account.address).call()
        assert balance_after == balance_before + amount

    def test_mint_by_no_minter_role(self, erc20wrapper):
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match="execution reverted: ERC20: must have minter role to mint"):
            erc20wrapper.mint_tokens(self.recipient_account, 10)
