import pytest

from integration.tests.basic.helpers.basic import BaseMixin


class TestChainId(BaseMixin):
    @pytest.fixture(scope="class")
    def contract(self, web3_client, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/ChainId", "0.8.10", class_account)
        return contract

    def test_chainId(self, contract):
        assert contract.functions.getCurrentValues().call() == 0

