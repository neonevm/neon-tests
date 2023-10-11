import pathlib

import solcx
from eth_account.signers.local import LocalAccount
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed
import spl.token.client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID

from . import web3client
from .metaplex import create_metadata_instruction_data, create_metadata_instruction

INIT_TOKEN_AMOUNT = 1000000000000000


class ERC20Wrapper:
    def __init__(
            self,
            web3_client: web3client.NeonWeb3Client,
            faucet,
            name,
            symbol,
            sol_client,
            solana_account,
            decimals=18,
            evm_loader_id=None,
            account=None,
            mintable=True,
    ):
        self.solana_associated_token_acc = None
        self.token_mint = None
        self.solana_acc = solana_account
        self.evm_loader_id = evm_loader_id
        self.web3_client = web3_client
        self.account = account
        if self.account is None:
            self.account = web3_client.create_account()
            faucet.request_neon(self.account.address, 300)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.sol_client = sol_client
        self.contract_address = self.deploy_wrapper(mintable)
        self.contract = self.get_wrapper_contract()

    def make_tx_object(self, from_address, gas_price=None, gas=None):
        tx = {
            "from": from_address,
            "nonce": self.web3_client.eth.get_transaction_count(from_address),
            "gasPrice": gas_price if gas_price is not None else self.web3_client.gas_price(),
        }
        if gas is not None:
            tx["gas"] = gas
        return tx

    def deploy_wrapper(self, mintable: bool):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "erc20_for_spl_factory", "0.8.10", self.account, contract_name="ERC20ForSplFactory"
        )
        assert contract_deploy_tx["status"] == 1, f"ERC20 Factory wasn't deployed: {contract_deploy_tx}"
        tx_object = self.make_tx_object(self.account.address)
        if mintable:

            instruction_tx = contract.functions.createErc20ForSplMintable(
                self.name, self.symbol, self.decimals, self.account.address
            ).build_transaction(tx_object)
        else:
            self.token_mint, self.solana_associated_token_acc = self.sol_client.create_spl(self.solana_acc,
                                                                                           self.decimals)
            metadata = create_metadata_instruction_data(self.name, self.symbol)
            txn = Transaction()
            txn.add(
                create_metadata_instruction(
                    metadata,
                    self.solana_acc.public_key,
                    self.token_mint.pubkey,
                    self.solana_acc.public_key,
                    self.solana_acc.public_key,
                )
            )
            self.sol_client.send_transaction(
                txn, self.solana_acc, opts=TxOpts(preflight_commitment=Confirmed, skip_confirmation=False)
            )
            instruction_tx = contract.functions.createErc20ForSpl(bytes(self.token_mint.pubkey)).build_transaction(
                tx_object
            )

        instruction_receipt = self.web3_client.send_transaction(self.account, instruction_tx)
        if instruction_receipt:
            logs = contract.events.ERC20ForSplCreated().process_receipt(instruction_receipt)
            return logs[0]["args"]["pair"]
        return instruction_receipt

    def get_wrapper_contract(self):
        contract_path = (pathlib.Path.cwd() / "contracts" / "EIPs" / "ERC20" / "IERC20ForSpl.sol").absolute()

        with open(contract_path, "r") as s:
            source = s.read()

        compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10")
        contract_interface = compiled[list(compiled.keys())[0]]

        contract = self.web3_client.eth.contract(address=self.contract_address, abi=contract_interface["abi"])
        return contract

    # TODO: In all this methods verify if exist self.account
    def mint_tokens(self, signer, to_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.mint(to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def claim(self, signer, from_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.claim(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def claim_to(self, signer, from_address, to_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.claimTo(from_address, to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn(self, signer, sender_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(sender_address, gas_price, gas)
        instruction_tx = self.contract.functions.burn(amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn_from(self, signer, from_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.burnFrom(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve(self, signer, spender_address, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.approve(spender_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        if isinstance(address_to, LocalAccount):
            address_to = address_to.address
        instruction_tx = self.contract.functions.transfer(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_solana(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.transferSolana(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve_solana(self, signer, spender, amount, gas_price=None, gas=None):
        tx = self.make_tx_object(signer.address, gas_price, gas)
        instruction_tx = self.contract.functions.approveSolana(spender, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def get_balance(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.balanceOf(address).call()
