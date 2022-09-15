import pathlib

import solcx
import eth_account.signers.local
from . import web3client


class ERC20Wrapper:
    def __init__(self, web3_client: web3client.NeonWeb3Client):
        self.web3_client = web3_client

    def deploy_wrapper(self, name, symbol, account: eth_account.signers.local.LocalAccount, decimals=18):
        solcx.install_solc("0.8.10")
        contract_path = (
                pathlib.Path.cwd() / "contracts" / "erc20_for_spl_factory.sol"
        ).absolute()

        with open(contract_path, "r") as s:
            source = s.read()
        compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10",
                                        base_path=pathlib.Path.cwd() / "contracts", optimize=True)
        contract_interface = compiled[list(compiled.keys())[0]]

        contract_deploy_tx = self.web3_client.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"]
        )

        contract = self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )
        instruction_tx = contract.functions.createErc20ForSplMintable(name, symbol, decimals,
                                                                      account.address).buildTransaction(
            {
                "from": account.address,
                "nonce": self.web3_client.eth.get_transaction_count(account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(account, instruction_tx)
        logs = contract.events.ERC20ForSplCreated().processReceipt(instruction_receipt)
        return contract, logs[0]["args"]["pair"]

    def get_wrapper_contract(self, contract_address):
        contract_path = (
                pathlib.Path.cwd() / "contracts" / "erc20interface.sol"
        ).absolute()

        with open(contract_path, "r") as s:
            source = s.read()

        compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10")
        contract_interface = compiled[list(compiled.keys())[0]]

        contract = self.web3_client.eth.contract(
            address=contract_address, abi=contract_interface["abi"]
        )
        return contract

    def mint_tokens(self, to_address, wrapped_contract, amount: int = 1000000000000000):
        instruction_tx = wrapped_contract.functions.mint(to_address.address, amount).buildTransaction(
            {
                "from": to_address.address,
                "nonce": self.web3_client.eth.get_transaction_count(to_address.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        resp = self.web3_client.send_transaction(to_address, instruction_tx)
        return resp
