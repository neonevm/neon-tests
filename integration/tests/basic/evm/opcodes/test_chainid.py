import pytest

from integration.tests.basic.helpers.basic import BaseMixin


class TestChainId(BaseMixin):
    @pytest.fixture(scope="class")
    def contract_neon(self, web3_client, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/ChainId", "0.8.10", class_account)
        return contract

    @pytest.fixture(scope="class")
    def contract_sol(self, web3_client_sol, class_account_sol_chain):
        contract, _ = web3_client_sol.deploy_and_get_contract(
            "opcodes/ChainId", "0.8.10", class_account_sol_chain)
        return contract

    def test_chain_id_sol(self, contract_sol, pytestconfig):
        assert contract_sol.functions.getCurrentValues().call() \
               == pytestconfig.environment.network_ids["sol"]

    def test_chain_id_neon(self, contract_neon, pytestconfig):
        assert contract_neon.functions.getCurrentValues().call() \
               == pytestconfig.environment.network_ids["neon"]
