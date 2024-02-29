import pathlib

import solcx
from eth_account.signers.local import LocalAccount
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from . import web3client
from .metaplex import create_metadata_instruction_data, create_metadata_instruction

INIT_TOKEN_AMOUNT = 1000000000000000


class ERC20Wrapper:
    def __init__(
        self,
        web3_client: web3client.NeonChainWeb3Client,
        faucet,
        name,
        symbol,
        sol_client,
        solana_account,
        decimals=9,
        evm_loader_id=None,
        account=None,
        mintable=True,
        contract_address=None,
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
        self.contract_address = contract_address

        if not contract_address:
            self.contract_address = self.deploy_wrapper(mintable)

        if mintable:
            self.contract = web3_client.get_deployed_contract(
                self.contract_address,
                contract_file="external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPLMintable",
                solc_version="0.8.24",
            )
        else:
            self.contract = web3_client.get_deployed_contract(
                self.contract_address,
                contract_file="external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPL",
                solc_version="0.8.24",
            )

    @property
    def address(self):
        """Compatibility with web3.eth.Contract"""
        return self.contract.address

    def _deploy_mintable_wrapper(self):
        beacon_erc20_impl, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPLMintable",
            "0.8.24",
            self.account,
            contract_name="ERC20ForSPLMintable",
        )
        assert tx["status"] == 1, f"ERC20ForSPLMintable wasn't deployed: {tx}"

        factory_contract, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPLMintableFactory",
            "0.8.24",
            self.account,
            contract_name="ERC20ForSPLMintableFactory",
        )
        assert tx["status"] == 1, f"ERC20ForSPLMintableFactory wasn't deployed: {tx}"

        proxy_contract, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/openzeppelin-fork/contracts/proxy/ERC1967/ERC1967Proxy",
            "0.8.24",
            self.account,
            contract_name="ERC1967Proxy",
            constructor_args=[
                factory_contract.address,
                factory_contract.encodeABI("initialize", [beacon_erc20_impl.address]),
            ],
        )
        assert tx["status"] == 1, f"ERC1967Proxy wasn't deployed: {tx}"

        factory_proxy_contract = self.web3_client.eth.contract(address=proxy_contract.address, abi=factory_contract.abi)

        return factory_proxy_contract

    def _deploy_not_mintable_wrapper(self):
        beacon_erc20_impl, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPL",
            "0.8.24",
            self.account,
            contract_name="ERC20ForSPL",
        )
        assert tx["status"] == 1, f"ERC20ForSPL wasn't deployed: {tx}"

        factory_contract, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/ERC20ForSPLFactory",
            "0.8.24",
            self.account,
            contract_name="ERC20ForSPLFactory",
        )
        assert tx["status"] == 1, f"ERC20ForSPL wasn't deployed: {tx}"

        proxy_contract, tx = self.web3_client.deploy_and_get_contract(
            "external/neon-contracts/ERC20ForSPL/contracts/openzeppelin-fork/contracts/proxy/ERC1967/ERC1967Proxy",
            "0.8.24",
            self.account,
            contract_name="ERC1967Proxy",
            constructor_args=[
                factory_contract.address,
                factory_contract.encodeABI("initialize", [beacon_erc20_impl.address]),
            ],
        )
        assert tx["status"] == 1, f"ERC1967Proxy wasn't deployed: {tx}"

        factory_proxy_contract = self.web3_client.eth.contract(address=proxy_contract.address, abi=factory_contract.abi)
        return factory_proxy_contract

    def _prepare_spl_token(self):
        self.token_mint, self.solana_associated_token_acc = self.sol_client.create_spl(self.solana_acc, self.decimals)
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

    def deploy_wrapper(self, mintable: bool):
        if mintable:
            contract = self._deploy_mintable_wrapper()
            tx_object = self.web3_client.make_raw_tx(self.account.address)
            instruction_tx = contract.functions.deploy(
                self.name, self.symbol, "http://uri.com", self.decimals
            ).build_transaction(tx_object)
        else:
            contract = self._deploy_not_mintable_wrapper()
            self._prepare_spl_token()
            tx_object = self.web3_client.make_raw_tx(self.account.address)
            instruction_tx = contract.functions.deploy(bytes(self.token_mint.pubkey)).build_transaction(tx_object)

        instruction_receipt = self.web3_client.send_transaction(self.account, instruction_tx)

        assert instruction_receipt["status"] == 1, f"Token wasn't deployed: {instruction_receipt}"
        if instruction_receipt:
            logs = contract.events.TokenDeploy().process_receipt(instruction_receipt)
            return logs[0]["args"]["token"]
        return instruction_receipt

    # TODO: In all this methods verify if exist self.account
    def mint_tokens(self, signer, to_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.mint(to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def claim(self, signer, from_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.claim(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def claim_to(self, signer, from_address, to_address, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.claimTo(from_address, to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn(self, signer, sender_address, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burn(amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn_from(self, signer, from_address, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burnFrom(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve(self, signer, spender_address, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approve(spender_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        if isinstance(address_to, LocalAccount):
            address_to = address_to.address
        instruction_tx = self.contract.functions.transfer(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_solana(self, signer, address_to, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferSolana(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve_solana(self, signer, spender, amount, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approveSolana(spender, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_ownership(self, signer, new_owner, gas_price=None, gas=None):
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferOwnership(new_owner).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def get_balance(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.balanceOf(address).call()
