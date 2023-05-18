import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_ADDRESS


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
        instruction_tx = contract.functions.transferOwnership(new_owner.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(acc, instruction_tx)
        assert receipt["status"] == 1
        assert contract.functions.owner().call() == new_owner.address

        event_logs = contract.events.OwnershipTransferred().process_receipt(receipt)
        assert len(event_logs) == 1
        assert event_logs[0].args['previousOwner'] == acc.address
        assert event_logs[0].args['newOwner'] == new_owner.address
        assert event_logs[0].event == "OwnershipTransferred"

    def test_only_owner_can_transfer_ownership(self, erc173):
        contract, acc = erc173
        not_owner = self.web3_client.create_account()
        self.faucet.request_neon(acc.address)
        tx = self.create_contract_call_tx_object(not_owner)

        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="Only the owner can perform this action",
        ):
            contract.functions.transferOwnership(not_owner.address).build_transaction(tx)

    def test_renounce_ownership(self, erc173):
        contract, acc = erc173
        tx = self.create_contract_call_tx_object(acc)
        instruction_tx = contract.functions.transferOwnership(ZERO_ADDRESS).build_transaction(tx)
        receipt = self.web3_client.send_transaction(acc, instruction_tx)

        assert receipt["status"] == 1
        assert contract.functions.owner().call() == ZERO_ADDRESS

    def test_contract_call_ownership_transfer(self, erc173):
        erc173_contract, acc = erc173
        erc173_caller_contract, _ = self.web3_client.deploy_and_get_contract(
            "ERC173", "0.8.10", acc, contract_name="ERC173Caller",
            constructor_args=[erc173_contract.address]
        )

        tx = self.create_contract_call_tx_object(acc)
        instruction_tx = erc173_contract.functions.\
            transferOwnership(erc173_caller_contract.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(acc, instruction_tx)
        assert receipt["status"] == 1

        new_owner = self.web3_client.create_account()
        self.faucet.request_neon(acc.address)
        tx = self.create_contract_call_tx_object(acc)
        instruction_tx = erc173_caller_contract.functions.\
            transferOwnership(new_owner.address).build_transaction(tx)

        receipt = self.web3_client.send_transaction(acc, instruction_tx)
        assert receipt["status"] == 1
        assert erc173_contract.functions.owner().call() == new_owner.address
