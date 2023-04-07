import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("Opcodes verifications")
@allure.story("EIP-211: New opcodes: RETURNDATASIZE and RETURNDATACOPY")
class TestReturnDataSizeAndCopyOpcodes(BaseMixin):
    @pytest.fixture(scope="class")
    def eip211_checker(self, web3_client, faucet):
        acc = web3_client.create_account()
        faucet.request_neon(acc.address, 100)
        contract, _ = web3_client.deploy_and_get_contract(
            "EIPs/EIP211_returndatasize_copy", "0.8.10", acc, contract_name="EIP211Checker")
        return contract

    def test_returndatasize(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions.setDataSize().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        data_size = eip211_checker.functions.dataSize().call()
        assert data_size == 96

    def test_returndatacopy(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions.setData().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        data = eip211_checker.functions.extractedData().call()
        assert 'teststring' in str(data)
