import allure

from clickfile import EnvName
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("ERC Verifications")
@allure.story("ERC-1820: Pseudo Introspection Registry Contract")
class TestERC1820PseudoIntrospectionRegistryContract:
    def test_pseudo_introspection_registry(
            self,
            web3_client: NeonChainWeb3Client,
            accounts: EthAccounts,
            env_name: EnvName,
    ):

        account = accounts[0]

        if env_name in (EnvName.DEVNET, EnvName.MAINNET):
            registry_address = "0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24"

        else:
            registry, _ = web3_client.deploy_and_get_contract(
                contract="EIPs/ERC1820PseudoIntrospectionRegistry.sol",

                version="0.5.3",
                account=account,
                contract_name="ERC1820Registry",
            )
            registry_address = registry.address

        contract_a, contract_a_receipt = web3_client.deploy_and_get_contract(
            contract="EIPs/ERC1820PseudoIntrospectionRegistry.sol",
            version="0.5.3",
            account=account,
            contract_name="ContractA",
            constructor_args=[registry_address],
        )

        contract_b, contract_b_receipt = web3_client.deploy_and_get_contract(
            contract="EIPs/ERC1820PseudoIntrospectionRegistry.sol",
            version="0.5.3",
            account=account,
            contract_name="ContractB",
            constructor_args=[registry_address, contract_a.address],
        )

        contract_manager, contract_setup_receipt = web3_client.deploy_and_get_contract(
            contract="EIPs/ERC1820PseudoIntrospectionRegistry.sol",
            version="0.5.3",
            account=account,
            contract_name="ContractManager",
            constructor_args=[registry_address, contract_a.address],
        )

        # Set ContractManager as the manager for ContractA
        tx_contract_manager = web3_client.make_raw_tx(from_=account)
        instruction_tx_contract_manager = contract_a.functions.setRegistryManager(
            contract_manager.address,
        ).build_transaction(tx_contract_manager)
        tx_contract_manager_receipt = web3_client.send_transaction(account, instruction_tx_contract_manager)
        assert tx_contract_manager_receipt.logs, "ERC1820Registry.setManager() failed"

        # ContractManager sets ContractA as the implementer for "sayHello" interface for ContractA address
        tx_contract_a = web3_client.make_raw_tx(from_=account)
        instruction_tx_contract_a = contract_manager.functions.registerInterface().build_transaction(tx_contract_a)
        tx_contract_a_receipt = web3_client.send_transaction(account, instruction_tx_contract_a)
        assert tx_contract_a_receipt.logs, "ERC1820Registry.setInterfaceImplementer() failed"

        # contractB queries registry to see what address implements "sayHello" for contractA address
        # in response gets the implementer address, and then calls sayHello() in it
        result = contract_b.functions.callSayHello(contract_manager.address).call()
        assert result == "Hello from ContractA", "ERC1820Registry.getInterfaceImplementer() failed"
