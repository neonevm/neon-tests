import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import generate_text

EXPECTED_RESULTS_STATIC = [("makeRevert()", "Revert msg"),
                           ("makeReturn()", "teststring"),
                           ("makeStop()", ""),
                           #    ("makeInvalid()", ""), INVALID opcode is not supported by Neon EVM
                           ]

EXPECTED_RESULTS = EXPECTED_RESULTS_STATIC + [("makeSelfdestruct()", "")]

DATA_0_96 = "0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000a74657374737472696e6700000000000000000000000000000000000000000000"
DATA_0_64 = "0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000020"
DATA_32_64 = "000000000000000000000000000000000000000000000000000000000000000a74657374737472696e67000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020"


@allure.feature("Opcodes verifications")
@allure.story("EIP-211: New opcodes: RETURNDATASIZE and RETURNDATACOPY")
class TestReturnDataSizeAndCopyOpcodes(BaseMixin):
    @pytest.fixture(scope="class")
    def eip211_checker(self, web3_client, faucet, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "EIPs/EIP211_returndatasize_copy", "0.8.10", class_account, contract_name="EIP211Checker")
        return contract

    def get_size_from_event_logs(self, contract, receipt):
        event_logs = contract.events.LogSize().process_receipt(receipt)
        return event_logs[0]['args']['size']

    def get_data_from_event_logs(self, contract, receipt):
        event_logs = contract.events.LogData().process_receipt(receipt)
        data = bytes(event_logs[0]['args']['data'])
        return web3.Web3.to_text(data[64:96].strip(b'\x00')).replace('\n', '')

    def test_returndatasize(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instr = eip211_checker.functions.getReturnDataSize().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instr)
        assert receipt["status"] == 1
        assert self.get_size_from_event_logs(eip211_checker, receipt) == 96

    @pytest.mark.parametrize("function, result", EXPECTED_RESULTS)
    def test_returndatacopy_for_call(self, eip211_checker, function, result):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instr = eip211_checker.functions.getReturnDataForCall(function).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instr)
        assert receipt["status"] == 1
        assert self.get_data_from_event_logs(eip211_checker, receipt) == result

    @pytest.mark.parametrize("function, result", EXPECTED_RESULTS_STATIC)
    def test_returndatacopy_for_delegatecall(self, eip211_checker, function, result):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions \
            .getReturnDataForDelegateCall(function).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_data_from_event_logs(eip211_checker, receipt) == result

    @pytest.mark.parametrize("function, result", EXPECTED_RESULTS_STATIC)
    def test_returndatacopy_for_staticcall(self, eip211_checker, function, result):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions \
            .getReturnDataForStaticCall(function).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_data_from_event_logs(eip211_checker, receipt) == result

    def test_returndatasize_for_create(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions.getReturnDataSizeForCreate().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_size_from_event_logs(eip211_checker, receipt) == 0

    def test_returndatasize_for_create2(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=10, max_len=200)
        instruction_tx = eip211_checker.functions.getReturnDataSizeForCreate2(salt).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_size_from_event_logs(eip211_checker, receipt) == 0

    def test_returndatacopy_for_create_with_revert(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions.getReturnDataForCreateWithRevert().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_data_from_event_logs(eip211_checker, receipt) == 'Revert msg'

    def test_returndatacopy_for_create2_with_revert(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=10, max_len=200)
        instruction_tx = eip211_checker.functions.getReturnDataForCreate2WithRevert(salt).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_data_from_event_logs(eip211_checker, receipt) == 'Revert msg'

    @pytest.mark.parametrize("position, size, expected_result", [(0, 64, DATA_0_64),
                                                                 (0, 96, DATA_0_96),
                                                                 (32, 64, DATA_32_64)])
    def test_returndatacopy_with_different_params(self, eip211_checker, position, size, expected_result):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip211_checker.functions.getReturnDataWithParams(position, size).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        event_logs = eip211_checker.events.LogData().process_receipt(receipt)
        data = bytes(event_logs[0]['args']['data'])
        assert data.hex() == expected_result

    def test_returndatacopy_with_invalid_params(self, eip211_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="exceeds data size"):
            eip211_checker.functions.getReturnDataWithParams(32, 96).build_transaction(tx)
