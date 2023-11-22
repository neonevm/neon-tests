import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_ADDRESS, MAX_UINT_256


@allure.feature("Opcodes verifications")
@allure.story("Unsupported opcode")
class TestUnsupportedOpcodes(BaseMixin):

    @pytest.fixture(scope="class")
    def contract(self, web3_client, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/UnsupportedOpcodes", "0.8.10", class_account)
        return contract

    def test_basefee(self, contract):
        assert contract.functions.baseFee().call() == 0

    def test_coinbase(self, contract):
        assert contract.functions.coinbase().call() == ZERO_ADDRESS

    def test_difficulty(self, contract):
        assert contract.functions.difficulty().call() == 0

    def test_gaslimit(self, contract):
        assert contract.functions.gaslimit().call() == MAX_UINT_256

    def test_gas_left(self, contract):
        assert contract.functions.gasLeft().call() == MAX_UINT_256
