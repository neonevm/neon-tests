import allure

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("Opcodes verifications")
@allure.story("Unsupported opcode")
class TestUnsupportedOpcodes(BaseMixin):

    def test_basefee(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/EIP3198_basefee", "0.8.10", self.sender_account, contract_name="basefeeCaller")
        basefee = contract.functions.baseFee().call()
        assert basefee == 0
