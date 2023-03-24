import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("ERC Verifications")
@allure.story(
    "ERC-173: Contract Ownership Standard"
)
class TestERC173ContractOwnershipStandard(BaseMixin):

    def test_ownership_transfer(self, erc173):
        contract, acc = erc173
        new_owner = self.web3_client.create_account()
        self.faucet.request_neon(acc.address)
        tx = self.create_contract_call_tx_object(acc)
        instruction_tx = contract.functions.transferOwnership(new_owner.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(acc, instruction_tx)
        assert receipt["status"] == 1
        assert contract.functions.owner().call() == new_owner.address

    def test_only_owner_can_transfer_ownership(self, erc173):
        contract, acc = erc173
        not_owner = self.web3_client.create_account()
        self.faucet.request_neon(acc.address)
        tx = self.create_contract_call_tx_object(not_owner)

        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="Only the owner can perform this action",
        ):
            contract.functions.transferOwnership(not_owner.address).buildTransaction(tx)
