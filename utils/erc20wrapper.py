from spl.token.client import Token
from eth_account.signers.local import LocalAccount
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from web3.types import TxReceipt

from . import web3client, stats_collector
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
        solana_account: Keypair,
        decimals=9,
        evm_loader_id=None,
        account=None,
        mintable=True,
        contract_address=None,
        bank_account=None,
    ):
        self.solana_associated_token_acc = None
        self.token_mint = None
        self.solana_acc = solana_account
        self.evm_loader_id = evm_loader_id
        self.web3_client = web3_client
        self.account = account
        if self.account is None:
            self.account = web3_client.create_account()
            if bank_account is not None:
                web3_client.send_neon(bank_account, self.account.address, 50)
            else:
                faucet.request_neon(self.account.address, 150)
        else:
            if bank_account is not None:
                web3_client.send_neon(bank_account, self.account.address, 50)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.sol_client = sol_client
        self.contract_address = contract_address
        self.token_mint: Token
        self.solana_associated_token_acc: Pubkey

        if contract_address:
            self.contract = web3_client.get_deployed_contract(contract_address, contract_file="EIPs/ERC20/IERC20ForSpl")
        else:
            self.contract_address = self.deploy_wrapper(mintable)
            self.contract = self.web3_client.get_deployed_contract(self.contract_address, "EIPs/ERC20/IERC20ForSpl")

    @property
    def address(self):
        """Compatibility with web3.eth.Contract"""
        return self.contract.address

    def _prepare_spl_token(self):
        self.token_mint, self.solana_associated_token_acc = self.sol_client.create_spl(self.solana_acc, self.decimals)
        metadata = create_metadata_instruction_data(self.name, self.symbol, uri="http://uri.com")
        txn = Transaction()
        txn.add(
            create_metadata_instruction(
                metadata,
                self.solana_acc.pubkey(),
                self.token_mint.pubkey,
                self.solana_acc.pubkey(),
                self.solana_acc.pubkey(),
            )
        )
        self.sol_client.send_transaction(
            txn, self.solana_acc, opts=TxOpts(preflight_commitment=Confirmed, skip_confirmation=False)
        )

    def deploy_wrapper(self, mintable: bool):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "neon-evm/erc20_for_spl_factory", "0.8.10", self.account, contract_name="ERC20ForSplFactory"
        )

        assert contract_deploy_tx["status"] == 1, f"ERC20 Factory wasn't deployed: {contract_deploy_tx}"

        tx_object = self.web3_client.make_raw_tx(self.account)
        if mintable:
            instruction_tx = contract.functions.createErc20ForSplMintable(
                self.name, self.symbol, self.decimals, self.account.address
            ).build_transaction(tx_object)
        else:
            self.token_mint, self.solana_associated_token_acc = self.sol_client.create_spl(
                self.solana_acc, self.decimals
            )
            self._prepare_spl_token()
            instruction_tx = contract.functions.createErc20ForSpl(bytes(self.token_mint.pubkey)).build_transaction(
                tx_object
            )

        instruction_receipt = self.web3_client.send_transaction(self.account, instruction_tx)
        if instruction_receipt:
            logs = contract.events.ERC20ForSplCreated().process_receipt(instruction_receipt)
            return logs[0]["args"]["pair"]
        return instruction_receipt

    # TODO: In all this methods verify if exist self.account
    @stats_collector.cost_report_from_receipt
    def mint_tokens(self, signer, to_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.mint(to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @stats_collector.cost_report_from_receipt
    def claim(self, signer, from_address, amount: int = INIT_TOKEN_AMOUNT, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.claim(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def claim_to(self, signer, from_address, to_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.claimTo(from_address, to_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @stats_collector.cost_report_from_receipt
    def burn(self, signer, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burn(amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def burn_from(self, signer, from_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burnFrom(from_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @stats_collector.cost_report_from_receipt
    def approve(self, signer, spender_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approve(spender_address, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @stats_collector.cost_report_from_receipt
    def transfer(self, signer, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        if isinstance(address_to, LocalAccount):
            address_to = address_to.address
        instruction_tx = self.contract.functions.transfer(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def transfer_solana(self, signer, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferSolana(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def approve_solana(self, signer, spender, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approveSolana(spender, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    def get_balance(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.balanceOf(address).call()
