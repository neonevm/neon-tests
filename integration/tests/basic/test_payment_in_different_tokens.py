import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("Multiply token")
@allure.story("Payments in sol tokens")
class TestSolChain(BaseMixin):

    @pytest.fixture(scope="class")
    def bob(self, class_account):
        return class_account

    @pytest.fixture(scope="class")
    def alice(self, web3_client, web3_client_sol, faucet, eth_bank_account):
        return web3_client_sol.create_account()

    @pytest.fixture(scope="function")
    def check_neon_balance_does_not_changed(self, alice, bob, web3_client):
        alica_balance_alica_before = web3_client.get_balance(alice)
        bob_balance_alica_before = web3_client.get_balance(bob)
        yield
        alica_balance_alica_after = web3_client.get_balance(alice)
        bob_balance_alica_after = web3_client.get_balance(bob)
        assert alica_balance_alica_after == alica_balance_alica_before
        assert bob_balance_alica_after == bob_balance_alica_before

    def test_user_to_user_trx(self, web3_client_sol, alice, bob,
                              check_neon_balance_does_not_changed):
        bob_sol_balance_before = web3_client_sol.get_balance(bob)
        alice_sol_balance_before = web3_client_sol.get_balance(alice)
        value = 10
        transaction = self.create_tx_object(bob.address, alice.address, value, web3_client=web3_client_sol)
        receipt = web3_client_sol.send_transaction(bob, transaction)
        assert receipt["status"] == 1
        bob_sol_balance_after = web3_client_sol.get_balance(bob)
        alice_sol_balance_after = web3_client_sol.get_balance(alice)
        assert alice_sol_balance_after == alice_sol_balance_before + web3_client_sol.to_main_currency(value)
        assert bob_sol_balance_after < bob_sol_balance_before - web3_client_sol.to_main_currency(value)

    def test_user_to_contract_and_contract_to_user_trx(self, web3_client_sol, bob,
                                                       check_neon_balance_does_not_changed,
                                                       wsol_contract):
        bob_sol_balance_before = web3_client_sol.get_balance(bob)
        contract_sol_balance_initial = web3_client_sol.get_balance(wsol_contract.address)
        amount = 10
        tx = self.make_contract_tx_object(bob.address, amount=amount, web3_client=web3_client_sol)
        instruction_tx = wsol_contract.functions.deposit().build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        bob_sol_balance_after_deposit = web3_client_sol.get_balance(bob)
        contract_sol_balance_after_deposit = web3_client_sol.get_balance(wsol_contract.address)
        assert contract_sol_balance_after_deposit == contract_sol_balance_initial + web3_client_sol.to_main_currency(
            amount)
        assert bob_sol_balance_after_deposit < bob_sol_balance_before - web3_client_sol.to_main_currency(amount)

        tx = self.make_contract_tx_object(bob.address, web3_client=web3_client_sol)
        instruction_tx = wsol_contract.functions.withdraw(
            web3_client_sol.to_main_currency(10)).build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        bob_sol_balance_after_withdraw = web3_client_sol.get_balance(bob)
        contract_sol_balance_after_withdraw = web3_client_sol.get_balance(wsol_contract.address)
        assert contract_sol_balance_after_withdraw == contract_sol_balance_initial
        assert bob_sol_balance_after_withdraw < bob_sol_balance_after_deposit + \
               web3_client_sol.to_main_currency(amount)

    def test_contract_to_contract_trx(self, web3_client_sol, bob):
        # contract to new contract
        amount = 1
        value = web3_client_sol.to_main_currency(amount)
        bob_sol_balance_before = web3_client_sol.get_balance(bob)
        wsol_contract_caller, resp = web3_client_sol.deploy_and_get_contract(
            contract="common/WNativeChainToken", version="0.8.12",
            contract_name="WNativeChainTokenCaller", account=bob, value=value
        )
        wrapper_address = wsol_contract_caller.events.Log().process_receipt(resp)[0].args["addr"]
        assert web3_client_sol.get_balance(wrapper_address) == value

        # contract to existing contract
        tx = self.make_contract_tx_object(bob.address, amount=amount, web3_client=web3_client_sol)
        instruction_tx = wsol_contract_caller.functions.deposit().build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        bob_sol_balance_after = web3_client_sol.get_balance(bob)

        assert web3_client_sol.get_balance(wrapper_address) == value * 2
        assert bob_sol_balance_after < bob_sol_balance_before - value * 2

    def test_user_to_contract_wrong_chain_id_trx(self, web3_client_sol, bob,
                                                 check_neon_balance_does_not_changed,
                                                 event_caller_contract):
        tx = self.make_contract_tx_object(bob.address, amount=1)
        instruction_tx = event_caller_contract.functions.unnamedArg("hello").build_transaction(tx)
        with pytest.raises(ValueError, match="wrong chain id"):
            self.web3_client_sol.send_transaction(bob, instruction_tx)

    def test_deploy_contract(self, web3_client_sol, bob,
                             check_neon_balance_does_not_changed):
        sol_balance_before = web3_client_sol.get_balance(bob)
        contract, _ = web3_client_sol.deploy_and_get_contract(
            contract="common/Common", version="0.8.12",
            contract_name="Common", account=bob,
        )
        sol_balance_after = web3_client_sol.get_balance(bob)
        assert sol_balance_after < sol_balance_before

    def test_deploy_contract_with_sending_tokens(self, web3_client_sol, bob,
                                                 check_neon_balance_does_not_changed):
        sol_bob_balance_before = web3_client_sol.get_balance(bob)
        value = 1000
        contract, receipt = web3_client_sol.deploy_and_get_contract(
            contract="common/WNativeChainToken", version="0.8.12",
            contract_name="WNativeChainToken", account=bob, value=value
        )
        assert receipt["status"] == 1
        sol_bob_balance_after = web3_client_sol.get_balance(bob)
        contract_balance = web3_client_sol.get_balance(contract.address)
        assert contract_balance == value
        assert sol_bob_balance_after < sol_bob_balance_before - value

    def test_deploy_contract_by_one_user_to_different_chain(self, web3_client_sol, new_account, alice,
                                                            web3_client):
        def deploy_contract(w3_client):
            _, rcpt = w3_client.deploy_and_get_contract(
                contract="common/Common", version="0.8.12",
                contract_name="Common", account=new_account
            )
            return rcpt

        deploy_contract(web3_client_sol)

        with pytest.raises(ValueError, match="EVM Error. Attempt to deploy to existing account"):
            deploy_contract(web3_client)

        # any transaction to raise the nonce
        web3_client.send_neon(new_account, alice, amount=1)

        receipt = deploy_contract(web3_client)
        assert receipt["status"] == 1
