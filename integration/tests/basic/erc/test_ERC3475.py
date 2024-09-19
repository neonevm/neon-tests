import allure
import pytest
import web3

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts

NONCE_ID = 0
CLASS_ID = 0


@allure.feature("EIP Verifications")
@allure.story("ERC-3475: Abstract Storage Bonds")
class TestAbstractStorageBonds:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def sender(self, faucet, web3_client, eth_bank_account):
        acc = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
        return acc

    @pytest.fixture(scope="class")
    def lender(self, faucet, web3_client, eth_bank_account):
        return web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)

    @pytest.fixture(scope="class")
    def secondary_buyer(self, faucet, web3_client, eth_bank_account):
        return web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)

    @pytest.fixture(scope="class")
    def operator(self, faucet, web3_client, eth_bank_account):
        return web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)

    @pytest.fixture(scope="class")
    def bond_contract(self, web3_client, sender):
        contract, _ = web3_client.deploy_and_get_contract("EIPs/ERC3475", "0.8.10", sender)
        return contract

    def issue(self, bond_contract, lender, sender, amount, class_id=CLASS_ID, nonce_id=NONCE_ID):
        trx_issuer = self.make_bond_single_trx(class_id, nonce_id, amount)
        tx = self.web3_client.make_raw_tx(sender)
        instr = bond_contract.functions.issue(lender.address, trx_issuer).build_transaction(tx)
        self.web3_client.send_transaction(sender, instr)

    @staticmethod
    def make_bond_single_trx(class_id=CLASS_ID, nonce_id=NONCE_ID, amount=7000):
        return [{"classId": class_id, "nonceId": nonce_id, "_amount": amount}]

    def test_issue_bonds_to_lender(self, sender, lender, bond_contract):
        balance_before = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        active_supply_before = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()

        self.issue(bond_contract, lender, sender, 7000)
        self.issue(bond_contract, lender, sender, 7000)

        balance = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        active_supply = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()
        assert balance - balance_before == 14000
        assert active_supply - active_supply_before == 14000

    def test_transfer_bonds(self, lender, secondary_buyer, bond_contract, sender):
        self.issue(bond_contract, lender, sender, 7000)

        transfer_bonds = self.make_bond_single_trx(amount=2000)

        lender_balance_before = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        buyer_balance_before = bond_contract.functions.balanceOf(secondary_buyer.address, CLASS_ID, NONCE_ID).call()
        active_supply_before = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()

        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.transferFrom(
            lender.address, secondary_buyer.address, transfer_bonds
        ).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)

        lender_balance = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        buyer_balance = bond_contract.functions.balanceOf(secondary_buyer.address, CLASS_ID, NONCE_ID).call()
        active_supply = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()
        assert lender_balance_before - lender_balance == 2000
        assert buyer_balance - buyer_balance_before == 2000
        assert active_supply - active_supply_before == 0

    def test_transfer_approved_bonds(self, lender, secondary_buyer, bond_contract, sender, operator):
        self.issue(bond_contract, lender, sender, 7000)
        trx_approval = self.make_bond_single_trx(amount=2000)
        lender_balance_before = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        buyer_balance_before = bond_contract.functions.balanceOf(secondary_buyer.address, CLASS_ID, NONCE_ID).call()
        operator_balance_before = bond_contract.functions.balanceOf(operator.address, CLASS_ID, NONCE_ID).call()
        active_supply_before = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()

        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.setApprovalFor(operator.address, True).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)

        assert bond_contract.functions.isApprovedFor(lender.address, operator.address).call() == True

        tx = self.web3_client.make_raw_tx(operator)
        instr = bond_contract.functions.transferFrom(
            lender.address, secondary_buyer.address, trx_approval
        ).build_transaction(tx)
        self.web3_client.send_transaction(operator, instr)

        lender_balance = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        buyer_balance = bond_contract.functions.balanceOf(secondary_buyer.address, CLASS_ID, NONCE_ID).call()
        operator_balance = bond_contract.functions.balanceOf(operator.address, CLASS_ID, NONCE_ID).call()
        active_supply = bond_contract.functions.activeSupply(CLASS_ID, NONCE_ID).call()
        assert lender_balance_before - lender_balance == 2000
        assert buyer_balance - buyer_balance_before == 2000
        assert active_supply - active_supply_before == 0
        assert operator_balance - operator_balance_before == 0

    def test_redeem_bonds(self, lender, bond_contract, sender):
        self.issue(bond_contract, lender, sender, 7000, 1, 1)
        lender_balance = bond_contract.functions.balanceOf(lender.address, 1, 1).call()
        redeem_trx = self.make_bond_single_trx(1, 1, lender_balance)
        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.redeem(lender.address, redeem_trx).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)
        lender_balance = bond_contract.functions.balanceOf(lender.address, 1, 1).call()
        assert lender_balance == 0

    def test_redeem_more_than_balance(self, lender, bond_contract, sender):
        class_id = 1
        nonce_id = 1
        self.issue(bond_contract, lender, sender, 7000, class_id, nonce_id)
        lender_balance = bond_contract.functions.balanceOf(lender.address, class_id, nonce_id).call()
        redeem_trx = self.make_bond_single_trx(class_id, nonce_id, lender_balance + 1000)
        tx = self.web3_client.make_raw_tx(lender)
        with pytest.raises(web3.exceptions.ContractLogicError, match="ERC3475: not enough bond to transfer"):
            bond_contract.functions.redeem(lender.address, redeem_trx).build_transaction(tx)

    def test_burn(self, lender, bond_contract, sender):
        self.issue(bond_contract, lender, sender, 7000)
        lender_balance = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        burn_trx = self.make_bond_single_trx(amount=lender_balance)
        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.burn(lender.address, burn_trx).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)
        lender_balance = bond_contract.functions.balanceOf(lender.address, CLASS_ID, NONCE_ID).call()
        assert lender_balance == 0

    def test_batch_approve_transfer_allowance(self, lender, bond_contract, sender, operator):
        trx_approve = [
            {"classId": CLASS_ID, "nonceId": NONCE_ID, "_amount": 500},
            {"classId": 1, "nonceId": NONCE_ID, "_amount": 900},
        ]
        tx = self.web3_client.make_raw_tx(sender)
        instr = bond_contract.functions.issue(lender.address, trx_approve).build_transaction(tx)
        self.web3_client.send_transaction(sender, instr)

        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.approve(operator.address, trx_approve).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)

        assert bond_contract.functions.allowance(lender.address, operator.address, CLASS_ID, NONCE_ID).call() == 500
        assert bond_contract.functions.allowance(lender.address, operator.address, 1, NONCE_ID).call() == 900

        tx = self.web3_client.make_raw_tx(operator)
        instr = bond_contract.functions.transferAllowanceFrom(
            lender.address, operator.address, trx_approve
        ).build_transaction(tx)
        self.web3_client.send_transaction(operator, instr)

        operator_balance1 = bond_contract.functions.balanceOf(operator.address, CLASS_ID, NONCE_ID).call()
        operator_balance2 = bond_contract.functions.balanceOf(operator.address, 1, NONCE_ID).call()
        assert operator_balance1 == 500
        assert operator_balance2 == 900

    def test_redeemed_supply(self, bond_contract, lender, sender):
        redeemed_supply_before = bond_contract.functions.redeemedSupply(CLASS_ID, NONCE_ID).call()

        self.issue(bond_contract, lender, sender, 7000)
        redeem_trx = self.make_bond_single_trx(amount=5000)
        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.redeem(lender.address, redeem_trx).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)
        redeemed_supply = bond_contract.functions.redeemedSupply(CLASS_ID, NONCE_ID).call()
        assert redeemed_supply - redeemed_supply_before == 5000

    def test_burned_supply(self, bond_contract, lender, sender):
        burned_supply_before = bond_contract.functions.burnedSupply(CLASS_ID, NONCE_ID).call()

        self.issue(bond_contract, lender, sender, 7000)
        burn_trx = self.make_bond_single_trx(amount=5000)
        tx = self.web3_client.make_raw_tx(lender)
        instr = bond_contract.functions.burn(lender.address, burn_trx).build_transaction(tx)
        self.web3_client.send_transaction(lender, instr)
        burned_supply = bond_contract.functions.burnedSupply(CLASS_ID, NONCE_ID).call()
        assert burned_supply - burned_supply_before == 5000

    def test_class_values(self, bond_contract):
        metadata_id = 0
        class_values = bond_contract.functions.classValues(CLASS_ID, metadata_id).call()
        assert class_values[0] == "DBIT Fix 6M"
        assert class_values[1] == 0
        assert class_values[2] == "0x0000000000000000000000000000000000000000"
        assert not class_values[3]

    def test_nonce_values(self, bond_contract):
        metadata_id = 0
        nonce_values = bond_contract.functions.nonceValues(CLASS_ID, NONCE_ID, metadata_id).call()
        assert nonce_values[0] == ""
        assert nonce_values[1] == 0
        assert nonce_values[2] == "0x0000000000000000000000000000000000000000"
        assert nonce_values[3]
