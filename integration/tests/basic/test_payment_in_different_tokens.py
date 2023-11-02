import random

import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import LAMPORT_PER_SOL


@allure.feature("Multiply token")
@allure.story("Payments in sol tokens")
class TestSolChain(BaseMixin):
    @pytest.fixture(scope="class")
    def bob(self, class_account_sol_chain):
        return class_account_sol_chain

    @pytest.fixture(scope="class")
    def alice(self, sol_client, web3_client, web3_client_sol,
              faucet, eth_bank_account, solana_account, pytestconfig):
        account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
        sol_client.request_airdrop(solana_account.public_key, 1 * LAMPORT_PER_SOL)
        sol_client.deposit_wrapped_sol_from_solana_to_neon(solana_account,
                                                           account,
                                                           web3_client_sol.eth.chain_id,
                                                           pytestconfig.environment.evm_loader,
                                                           1 * LAMPORT_PER_SOL)
        return account

    @pytest.fixture(scope="function")
    def check_neon_balance_does_not_changed(self, alice, bob, web3_client):
        alice_balance_before = web3_client.get_balance(alice)
        bob_balance_before = web3_client.get_balance(bob)
        yield
        alice_balance_after = web3_client.get_balance(alice)
        bob_balance_after = web3_client.get_balance(bob)
        assert alice_balance_after == alice_balance_before
        assert bob_balance_after == bob_balance_before

    def test_user_to_user_trx(self, web3_client_sol, alice, bob,
                              check_neon_balance_does_not_changed):
        bob_sol_balance_before = web3_client_sol.get_balance(bob)
        alice_sol_balance_before = web3_client_sol.get_balance(alice)
        value = 1000
        receipt = web3_client_sol.send_tokens(bob, alice, value)
        assert receipt["status"] == 1
        bob_sol_balance_after = web3_client_sol.get_balance(bob)
        alice_sol_balance_after = web3_client_sol.get_balance(alice)
        assert alice_sol_balance_after == alice_sol_balance_before + value
        assert bob_sol_balance_after < bob_sol_balance_before - value

    def test_user_to_contract_and_contract_to_user_trx(self, web3_client_sol, bob,
                                                       check_neon_balance_does_not_changed,
                                                       wsol):
        bob_sol_balance_before = web3_client_sol.get_balance(bob)
        contract_sol_balance_initial = web3_client_sol.get_balance(wsol.address)
        amount = 10
        tx = self.make_contract_tx_object(bob.address, amount=amount, web3_client=web3_client_sol)
        instruction_tx = wsol.functions.deposit().build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        bob_sol_balance_after_deposit = web3_client_sol.get_balance(bob)
        contract_sol_balance_after_deposit = web3_client_sol.get_balance(wsol.address)
        assert contract_sol_balance_after_deposit == contract_sol_balance_initial + web3_client_sol.to_main_currency(
            amount)
        assert bob_sol_balance_after_deposit < bob_sol_balance_before - web3_client_sol.to_main_currency(amount)

        tx = self.make_contract_tx_object(bob.address, web3_client=web3_client_sol)
        instruction_tx = wsol.functions.withdraw(
            web3_client_sol.to_main_currency(10)).build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        bob_sol_balance_after_withdraw = web3_client_sol.get_balance(bob)
        contract_sol_balance_after_withdraw = web3_client_sol.get_balance(wsol.address)
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

    def test_deploy_contract(self, web3_client_sol, alice,
                             check_neon_balance_does_not_changed):
        sol_balance_before = web3_client_sol.get_balance(alice)
        contract, _ = web3_client_sol.deploy_and_get_contract(
            contract="common/Common", version="0.8.12",
            contract_name="Common", account=alice,
        )
        sol_balance_after = web3_client_sol.get_balance(alice)
        assert sol_balance_after < sol_balance_before

    def test_deploy_contract_with_sending_tokens(self, web3_client_sol, alice,
                                                 check_neon_balance_does_not_changed):
        sol_alice_balance_before = web3_client_sol.get_balance(alice)
        value = 1000
        contract, receipt = web3_client_sol.deploy_and_get_contract(
            contract="common/WNativeChainToken", version="0.8.12",
            contract_name="WNativeChainToken", account=alice, value=value
        )
        assert receipt["status"] == 1
        sol_alice_balance_after = web3_client_sol.get_balance(alice)
        contract_balance = web3_client_sol.get_balance(contract.address)
        assert contract_balance == value
        assert sol_alice_balance_after < sol_alice_balance_before - value

    def test_deploy_contract_by_one_user_to_different_chain(self, web3_client_sol, new_account,
                                                            solana_account, alice,
                                                            web3_client, pytestconfig):
        def deploy_contract(w3_client):
            _, rcpt = w3_client.deploy_and_get_contract(
                contract="common/Common", version="0.8.12",
                contract_name="Common", account=new_account
            )
            return rcpt

        self.sol_client.deposit_wrapped_sol_from_solana_to_neon(solana_account,
                                                                new_account,
                                                                web3_client_sol.eth.chain_id,
                                                                pytestconfig.environment.evm_loader)

        deploy_contract(web3_client_sol)

        with pytest.raises(ValueError, match="EVM Error. Attempt to deploy to existing account"):
            deploy_contract(web3_client)

        # any transaction to raise the nonce
        web3_client.send_neon(new_account, alice, amount=1)

        receipt = deploy_contract(web3_client)
        assert receipt["status"] == 1
        print(web3_client_sol.get_nonce(new_account))
        print(web3_client.get_nonce(new_account))

    # web3_client_sol.send_tokens(new_account, alice, value=10)

    def test_interact_with_contract_from_another_chain(self, web3_client_sol, bob,
                                                       check_neon_balance_does_not_changed,
                                                       common_contract):
        tx = self.make_contract_tx_object(bob.address, web3_client=web3_client_sol)
        common_contract_sol_chain = web3_client_sol.get_deployed_contract(
            common_contract.address, "common/Common")
        number = random.randint(0, 1000000)
        instruction_tx = common_contract_sol_chain.functions.setNumber(number).build_transaction(tx)

        self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert common_contract_sol_chain.functions.getNumber().call() == number
        assert common_contract.functions.getNumber().call() == number

    def test_transfer_neons_in_sol_chain(self, web3_client_sol, web3_client, bob, alice, wneon):
        amount = 12
        value = self.web3_client._web3.to_wei(amount, "ether")

        tx = self.make_contract_tx_object(bob.address, amount=amount)

        instruction_tx = wneon.functions.deposit().build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        wneon_sol_chain = web3_client_sol.get_deployed_contract(
            wneon.address, "common/WNeon", "WNEON", "0.4.26")

        tx = self.make_contract_tx_object(bob.address, web3_client=web3_client_sol)
        neon_balance_before = web3_client.get_balance(alice.address)
        instruction_tx = wneon_sol_chain.functions.transfer(alice.address, value).build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1

        tx = self.make_contract_tx_object(alice.address, web3_client=web3_client_sol)
        instruction_tx = wneon_sol_chain.functions.withdraw(value).build_transaction(tx)
        receipt = self.web3_client_sol.send_transaction(alice, instruction_tx)
        assert receipt["status"] == 1

        assert web3_client.get_balance(alice.address) == neon_balance_before + amount

    def test_transfer_sol_in_neon_chain(self, web3_client_sol, web3_client, bob, alice, wsol):
        amount = 12
        value = web3_client_sol.to_main_currency(amount)

        tx = self.make_contract_tx_object(bob.address, amount=amount, web3_client=web3_client_sol)

        instruction_tx = wsol.functions.deposit().build_transaction(tx)
        self.web3_client_sol.send_transaction(bob, instruction_tx)

        wsol_neon_chain = web3_client.get_deployed_contract(
            wsol.address, "common/WNativeChainToken")

        tx = self.make_contract_tx_object(bob.address, web3_client=web3_client)
        sol_balance_before = web3_client_sol.get_balance(alice.address)
        instruction_tx = wsol_neon_chain.functions.transfer(alice.address, value).build_transaction(tx)
        receipt = self.web3_client.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1

        tx = self.make_contract_tx_object(alice.address, web3_client=web3_client)
        instruction_tx = wsol_neon_chain.functions.withdraw(value).build_transaction(tx)
        receipt = self.web3_client.send_transaction(alice, instruction_tx)
        assert receipt["status"] == 1

        assert web3_client_sol.get_balance(alice.address) == sol_balance_before + value
