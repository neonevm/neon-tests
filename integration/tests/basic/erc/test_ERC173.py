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
    @pytest.fixture(scope="function")
    def erc173(self):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "EIPs/ERC173", "0.8.10", self.sender_account
        )
        return contract

    def test_ownership_transfer(self, erc173, new_account):
        new_owner = new_account
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = erc173.functions.transferOwnership(new_owner.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert erc173.functions.owner().call() == new_owner.address

        event_logs = erc173.events.OwnershipTransferred().process_receipt(receipt)
        assert len(event_logs) == 1
        assert event_logs[0].args['previousOwner'] == self.sender_account.address
        assert event_logs[0].args['newOwner'] == new_owner.address
        assert event_logs[0].event == "OwnershipTransferred"

    def test_only_owner_can_transfer_ownership(self, erc173, new_account):
        tx = self.create_contract_call_tx_object(new_account)

        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="Only the owner can perform this action",
        ):
            erc173.functions.transferOwnership(new_account.address).build_transaction(tx)

    def test_renounce_ownership(self, erc173):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = erc173.functions.transferOwnership(ZERO_ADDRESS).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        assert receipt["status"] == 1
        assert erc173.functions.owner().call() == ZERO_ADDRESS

    def test_contract_call_ownership_transfer(self, erc173, new_account):
        erc173_caller_contract, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/ERC173", "0.8.10", self.sender_account, contract_name="ERC173Caller",
            constructor_args=[erc173.address]
        )

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = erc173.functions.\
            transferOwnership(erc173_caller_contract.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        new_owner = new_account
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = erc173_caller_contract.functions.\
            transferOwnership(new_owner.address).build_transaction(tx)

        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert erc173.functions.owner().call() == new_owner.address
