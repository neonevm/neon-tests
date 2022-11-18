import pytest
import solcx
import web3

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import get_contract_abi


class TestContractReverting(BaseMixin):

    @pytest.fixture(scope="class")
    def solc_version(self):
        version = '0.7.0'
        if version not in [str(v) for v in solcx.get_installed_solc_versions()]:
            solcx.install_solc(version)
        return version

    def test_constructor_raises_string_based_error(self, solc_version):
        contract = '''
            pragma solidity >=0.7.0 <0.9.0;
            contract ArrConstructable {
                constructor(uint256[] memory vector_) payable {
                    require(vector_.length > 0, "ListConstructable: empty list");
                }
            }
        '''
        compiled = solcx.compile_source(contract,
                                        output_values=["abi", "bin"],
                                        solc_version=solc_version
                                        )  # this allow_paths isn't very good...
        contract_interface = get_contract_abi("ArrConstructable", compiled)
        contract = self.web3_client.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match="execution reverted: ListConstructable: empty list"):
            contract.constructor([]).buildTransaction()

    def test_constructor_raises_no_argument_error(self, solc_version):
        contract = '''
            pragma solidity >=0.7.0 <0.9.0;
            contract ArrConstructable {
                constructor(uint256[] memory vector_) payable {
                    require(vector_.length > 0);
                }
            }
        '''

        compiled = solcx.compile_source(contract,
                                        output_values=["abi", "bin"],
                                        solc_version=solc_version
                                        )  # this allow_paths isn't very good...
        contract_interface = get_contract_abi("ArrConstructable", compiled)
        contract = self.web3_client.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])

        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            contract.constructor([]).buildTransaction()

    def test_method_raises_string_based_error(self):
        contract, _ = self.web3_client.deploy_and_get_contract("trivial_revert", "0.7.0",
                                                               self.sender_account, contract_name="TrivialRevert",
                                                               constructor_args=[]
                                                               )
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted: Predefined revert happened"):
            contract.functions.do_string_based_revert().call()

    def test_method_raises_trivial_error(self):
        contract, _ = self.web3_client.deploy_and_get_contract("trivial_revert", "0.7.0",
                                                               self.sender_account, contract_name="TrivialRevert",
                                                               constructor_args=[]
                                                               )
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            contract.functions.do_trivial_revert().call()
