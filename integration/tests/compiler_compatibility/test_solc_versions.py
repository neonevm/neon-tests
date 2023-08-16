import pytest
import solcx
from integration.tests.compiler_compatibility.helpers.erc_20_common_checks import Erc20CommonChecks
from utils.helpers import generate_text

INIT_NAME = "SampleToken"
INIT_SYMBOL = "ST"
INIT_DECIMALS = 18
INIT_SUPPLY = 1000


class SolcVersions:
    def __init__(self):
        self.instances = [str(item) for item in solcx.get_installable_solc_versions()[0:3]]


class TestSolcCompatibility(Erc20CommonChecks):

    @staticmethod
    def load_data():
        versions = SolcVersions().instances
        result = {"params": versions, "ids": versions}
        return result

    @pytest.fixture(scope="class", **load_data())
    def solc_version(self, request):
        return request.param

    @pytest.mark.parametrize()
    @pytest.fixture(scope="class")
    def erc20_solc(self, web3_client, class_account, solc_version):
        contract, _ = web3_client.deploy_and_get_contract(
            "ERC20/ERC20.sol",
            solc_version,
            class_account,
            contract_name="ERC20",
            constructor_args=[INIT_NAME, INIT_SYMBOL, INIT_SUPPLY],
        )
        return contract

    @pytest.fixture(scope="class")
    def recursion_factory(self, class_account, web3_client, solc_version):
        contract, _ = web3_client.deploy_and_get_contract(
            "Recursion", solc_version, class_account,
            contract_name="DeployRecursionFactory",
            constructor_args=[3])
        return contract

    def test_name(self, erc20_solc):
        assert erc20_solc.functions.name().call() == INIT_NAME

    def test_mint(self, erc20_solc, class_account):
        self.check_erc20_mint_function(erc20_solc, class_account)

    def test_transfer(self, erc20_solc, class_account, new_account):
        self.check_erc20_transfer_function(erc20_solc, class_account, new_account)

    def test_deploy_contract_by_contract(self, recursion_factory, class_account):
        tx = self.create_tx_object(class_account.address, estimate_gas=False)
        salt = generate_text(min_len=5, max_len=7)
        instruction_tx = recursion_factory.functions.deploySecondContractViaCreate2(salt).build_transaction(tx)
        receipt = self.web3_client.send_transaction(class_account, instruction_tx)
        assert receipt["status"] == 1

        event_logs = recursion_factory.events.SecondContractDeployed().process_receipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert len(addresses) == 2
