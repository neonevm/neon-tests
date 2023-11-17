import pytest

from integration.tests.basic.helpers.basic import BaseMixin


class TestChainIdDependentOpcodes(BaseMixin):
    @pytest.fixture(scope="class")
    def contract_neon(self, web3_client, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/ChainIdDependentOpCodes", "0.8.10", class_account)
        return contract

    @pytest.fixture(scope="class")
    def contract_neon_caller(self, web3_client_sol, class_account):
        contract, _ = web3_client_sol.deploy_and_get_contract(
            "opcodes/ChainIdDependentOpCodes", "0.8.10", class_account,
            contract_name='ChainIdDependentOpCodesCaller',
            constructor_args=[class_account.address],
        )
        return contract

    @pytest.fixture(scope="class")
    def contract_sol(self, web3_client_sol, class_account_sol_chain):
        contract, _ = web3_client_sol.deploy_and_get_contract(
            "opcodes/ChainIdDependentOpCodes", "0.8.10", class_account_sol_chain)
        return contract

    @pytest.fixture(scope="class")
    def contract_caller_sol(self, web3_client_sol, class_account_sol_chain):
        contract, _ = web3_client_sol.deploy_and_get_contract(
            "opcodes/ChainIdDependentOpCodes", "0.8.10", class_account_sol_chain,
            contract_name='ChainIdDependentOpCodesCaller',
        )
        return contract

    @pytest.fixture(scope="class")
    def contract_caller_neon(self, web3_client, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/ChainIdDependentOpCodes", "0.8.10", class_account,
            contract_name='ChainIdDependentOpCodesCaller',
        )
        return contract

    @pytest.mark.multipletokens
    def test_chain_id_sol(self, contract_sol, pytestconfig):
        assert contract_sol.functions.getChainId().call() \
               == pytestconfig.environment.network_ids["sol"]

    def test_chain_id_neon(self, contract_neon, pytestconfig):
        assert contract_neon.functions.getChainId().call() \
               == pytestconfig.environment.network_ids["neon"]

    @pytest.mark.multipletokens
    def test_balance_by_sol_contract(self, contract_sol, class_account_sol_chain, web3_client,
                                     web3_client_sol, contract_caller_sol):
        # user calls sol contract in sol chain == sol balance
        # user calls sol contract in neon chain == neon balance
        # sol contract calls sol contract in sol chain == sol balance
        # sol contract calls sol contract in neon chain == sol balance

        expected_balance_sol = web3_client_sol.get_balance(class_account_sol_chain.address)
        expected_balance_neon = web3_client.get_balance(class_account_sol_chain.address)
        balance = contract_sol.functions.getBalance(class_account_sol_chain.address).call()

        assert balance == expected_balance_sol

        contract_sol_in_neon_network = web3_client.get_deployed_contract(contract_sol.address,
                                                                         "opcodes/ChainIdDependentOpCodes")
        balance = contract_sol_in_neon_network.functions.getBalance(class_account_sol_chain.address).call()
        assert balance == expected_balance_neon

        balance = contract_caller_sol.functions.getBalance(contract_sol.address, class_account_sol_chain.address).call()
        assert balance == expected_balance_sol

        caller_in_neon_network = web3_client.get_deployed_contract(contract_caller_sol.address,
                                                                   'opcodes/ChainIdDependentOpCodes',
                                                                   'ChainIdDependentOpCodesCaller')

        balance = caller_in_neon_network.functions.getBalance(contract_sol.address,
                                                              class_account_sol_chain.address).call()
        assert balance == expected_balance_sol

    @pytest.mark.multipletokens
    def test_balance_by_neon_contract(self, contract_neon, sol_client, class_account, web3_client,
                                      web3_client_sol, contract_caller_neon):
        # user call neon contract in neon chain == neon balance
        # user calls neon contract in sol chain == sol balance
        # neon contract calls neon contract in neon chain == neon balance
        # neon contract calls neon contract in sol chain == neon balance

        expected_balance_sol = web3_client_sol.get_balance(class_account.address)
        expected_balance_neon = web3_client.get_balance(class_account.address)

        balance = contract_neon.functions.getBalance(class_account.address).call()
        assert balance == expected_balance_neon

        contract_neon_in_sol_network = web3_client_sol.get_deployed_contract(contract_neon.address,
                                                                             "opcodes/ChainIdDependentOpCodes")
        balance = contract_neon_in_sol_network.functions.getBalance(class_account.address).call()
        assert balance == expected_balance_sol

        caller_in_sol_network = web3_client_sol.get_deployed_contract(contract_caller_neon.address,
                                                                      'opcodes/ChainIdDependentOpCodes',
                                                                      'ChainIdDependentOpCodesCaller')

        balance = caller_in_sol_network.functions.getBalance(contract_neon.address, class_account.address).call()
        assert balance == expected_balance_neon

        balance = caller_in_sol_network.functions.getBalance(contract_neon.address,
                                                             class_account.address).call()
        assert balance == expected_balance_neon
