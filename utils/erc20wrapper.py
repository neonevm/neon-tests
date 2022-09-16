import pathlib

import solcx
from . import web3client


class ERC20Wrapper:
    def __init__(self, web3_client: web3client.NeonWeb3Client, faucet, name, symbol, decimals=18):
        self.web3_client = web3_client
        self.account = web3_client.create_account()
        faucet.request_neon(self.account.address, 100)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.contract_address = self.deploy_wrapper()
        self.contract = self.get_wrapper_contract()

    def deploy_wrapper(self):
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
            self.account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"]
        )

        contract = self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )
        instruction_tx = contract.functions.createErc20ForSplMintable(self.name, self.symbol, self.decimals,
                                                                      self.account.address).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(self.account, instruction_tx)
        logs = contract.events.ERC20ForSplCreated().processReceipt(instruction_receipt)
        return logs[0]["args"]["pair"]

    def get_wrapper_contract(self):
        contract_path = (
                pathlib.Path.cwd() / "contracts" / "erc20interface.sol"
        ).absolute()

        with open(contract_path, "r") as s:
            source = s.read()

        compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10")
        contract_interface = compiled[list(compiled.keys())[0]]

        contract = self.web3_client.eth.contract(
            address=self.contract_address, abi=contract_interface["abi"]
        )
        return contract

    def mint_tokens(self, to_address, amount: int = 1000000000000000):
        instruction_tx = self.contract.functions.mint(to_address.address, amount).buildTransaction(
            {
                "from": to_address.address,
                "nonce": self.web3_client.eth.get_transaction_count(to_address.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        resp = self.web3_client.send_transaction(to_address, instruction_tx)
        return resp
