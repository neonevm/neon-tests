import allure
import pytest

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Go-ethereum opCodes tests")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestOpcodeCall:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def contract_staticcaller(self, web3_client, faucet, accounts):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/StaticCall.sol",
            "0.8.0",
            accounts[0],
            contract_name="StaticCaller",
        )
        return contract

    def test_staticcall(self, counter_contract, contract_staticcaller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)

        inc_instruction_tx = counter_contract.functions.inc().build_transaction(tx)
        self.web3_client.send_transaction(sender_account, inc_instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_staticcaller.functions.callGet(counter_contract.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        count_from_log = contract_staticcaller.events.Log().process_receipt(resp)[0]["args"]["counter_value"]
        assert count_from_log == 1

    def test_change_state(self, counter_contract, contract_staticcaller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)

        inc_instruction_tx = counter_contract.functions.inc().build_transaction(tx)
        self.web3_client.send_transaction(sender_account, inc_instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_staticcaller.functions.callInc(counter_contract.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        successfull = contract_staticcaller.events.LogSuccess().process_receipt(resp)[0]["args"]["success"]
        assert not successfull

    def test_limit_gas_lower_underestimate(self, counter_contract, contract_staticcaller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)

        inc_instruction_tx = counter_contract.functions.inc().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, inc_instruction_tx)
        assert receipt["status"] == 1

        tx = self.web3_client.make_raw_tx(sender_account, gas=2500)
        instruction_tx = contract_staticcaller.functions.callGet(counter_contract.address).build_transaction(tx)

        with pytest.raises(ValueError):
            self.web3_client.send_transaction(sender_account, instruction_tx)
