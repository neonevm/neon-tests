import allure
import pytest
import web3

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Go-ethereum opCodes tests")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestOpCodes:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def opcodes_checker(self, web3_client, faucet, accounts):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/BaseOpCodes", "0.5.16", accounts[0], contract_name="BaseOpCodes"
        )
        return contract

    def test_base_opcodes(self, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_stop(self, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test_stop().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_invalid_opcode(self, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="EVM encountered invalid opcode"):
            opcodes_checker.functions.test_invalid().build_transaction(tx)

    def test_revert(self, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            opcodes_checker.functions.test_revert().build_transaction(tx)
