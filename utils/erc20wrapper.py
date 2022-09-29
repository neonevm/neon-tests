import pathlib

import solcx
from . import web3client


class ERC20Wrapper:
    def __init__(self, web3_client: web3client.NeonWeb3Client, faucet, name, symbol, decimals=18, account=None):
        self.web3_client = web3_client
        self.account = account or web3_client.create_account()
        faucet.request_neon(self.account.address, 100)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.contract_address = self.deploy_wrapper()
        self.contract = self.get_wrapper_contract()

    def make_tx_object(self, from_address, gasPrice=None, gas=None):
        tx = {"from": from_address, "nonce": self.web3_client.eth.get_transaction_count(from_address),
              "gasPrice": gasPrice if gasPrice is not None else self.web3_client.gas_price()}
        if gas is not None:
            tx["gas"] = gas
        return tx

    def deploy_wrapper(self):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "erc20_for_spl_factory", "0.8.10", self.account, contract_name='ERC20ForSplFactory')
        tx_object = self.make_tx_object(self.account.address)
        instruction_tx = contract.functions.createErc20ForSplMintable(self.name, self.symbol, self.decimals,
                                                                      self.account.address).buildTransaction(tx_object)
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

    def mint_tokens(self, signer, to_address, amount: int = 1000000000000000, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.mint(to_address, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn(self, signer, sender_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(sender_address, gas_price, gas)
        instruction_tx = self.contract.functions.burn(amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn_from(self, signer, from_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.burnFrom(from_address, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve(self, signer, spender_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.approve(spender_address, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.transfer(address_to, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_solana(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.transferSolana(address_to, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve_solana(self, signer, spender, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.approveSolana(spender, amount).buildTransaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp
