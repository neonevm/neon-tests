from typing import Union

from eth_account.signers.local import LocalAccount
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import approve, ApproveParams
from web3.types import TxReceipt

from . import web3client, stats_collector
from .consts import REMAPPING_ZEPPELIN
from .evm_loader import EvmLoader
from .metaplex import create_metadata_instruction_data, create_metadata_instruction
from .neon_user import NeonUser

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
        owner=None,
        mintable=True,
        contract_address=None,
        bank_account=None,
    ) -> None:
        self.web3_client = web3_client
        self.sol_client = sol_client
        self.solana_acc = solana_account
        self.name = name
        self.symbol = symbol
        self.decimals = decimals
        self.contract_address = contract_address
        self.solana_associated_token_acc: Union[Pubkey, None] = None

        self.owner = owner or self._create_or_fund_owner(faucet, bank_account)

        if not self.contract_address:
            self.contract_address = self.deploy_wrapper(mintable)

        self.contract_name = "ERC20ForSplMintable" if mintable else "ERC20ForSpl"

        self.contract = self.web3_client.get_deployed_contract(
            self.contract_address,
            contract_name=self.contract_name,
            contract_file="neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl",
            solc_version="0.8.28",
            import_remapping=REMAPPING_ZEPPELIN,
        )

        self.token_mint_pubkey = Pubkey(self.contract.functions.tokenMint().call())
        self.token_mint: Token

    def _create_or_fund_owner(self, faucet, bank_account):
        owner = self.web3_client.create_account()
        if bank_account:
            self.web3_client.send_neon(bank_account, owner.address, 50)
        else:
            faucet.request_neon(owner.address, 150)
        return owner

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
            "neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl_factory",
            "0.8.28",
            self.owner,
            contract_name="ERC20ForSplFactory",
            import_remapping=REMAPPING_ZEPPELIN,
        )

        assert contract_deploy_tx["status"] == 1, f"ERC20 wasn't deployed: {contract_deploy_tx}"

        tx_object = self.web3_client.make_raw_tx(self.owner)
        if mintable:
            instruction_tx = contract.functions.createErc20ForSplMintable(
                self.name, self.symbol, self.decimals, self.owner.address
            ).build_transaction(tx_object)
        else:
            self.token_mint, self.solana_associated_token_acc = self.sol_client.create_spl(
                self.solana_acc, self.decimals
            )
            self._prepare_spl_token()
            instruction_tx = contract.functions.createErc20ForSpl(bytes(self.token_mint.pubkey)).build_transaction(
                tx_object
            )

        instruction_receipt = self.web3_client.send_transaction(self.owner, instruction_tx)
        if instruction_receipt:
            logs = contract.events.ERC20ForSplCreated().process_receipt(instruction_receipt)
            return logs[0]["args"]["pair"]
        return instruction_receipt

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
        return self.web3_client.send_transaction(signer, instruction_tx)

    def claim_to(self, signer, from_address, to_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.claimTo(from_address, to_address, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    @stats_collector.cost_report_from_receipt
    def burn(self, signer, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burn(amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    def burn_from(self, signer, from_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.burnFrom(from_address, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    @stats_collector.cost_report_from_receipt
    def approve(self, signer, spender_address, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approve(spender_address, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    @stats_collector.cost_report_from_receipt
    def transfer(self, signer, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        if isinstance(address_to, LocalAccount):
            address_to = address_to.address
        instruction_tx = self.contract.functions.transfer(address_to, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    @stats_collector.cost_report_from_receipt
    def transfer_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    def transfer_solana(self, signer, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferSolana(address_to, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    def transfer_solana_from(self, signer, address_from, address_to, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferSolanaFrom(address_from, address_to, amount).build_transaction(
            tx
        )
        return self.web3_client.send_transaction(signer, instruction_tx)

    def approve_solana(self, signer, spender, amount, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approveSolana(spender, amount).build_transaction(tx)
        return self.web3_client.send_transaction(signer, instruction_tx)

    def get_balance(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.balanceOf(address).call()

    def get_user_ext_authority(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.getUserExtAuthority(address).call()

    def get_account_delegate_data(self, address) -> list[bytes, int]:
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.getAccountDelegateData(address).call()

    def get_solana_account(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.solanaAccount(address).call()

    def get_token_mint_ata(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.getTokenMintATA(address).call()

    def pop_up_balance(
        self,
        evm_loader: EvmLoader,
        recipient: NeonUser,
        pda_amount: int,
        ata_amount: int,
        approve_ata_amount: int = None,
    ) -> None:
        """
        Top up a recipient's token balances by transferring tokens to both their PDA and ATA accounts.

        Parameters:
        recipient: The target user object receiving the token top-up.
        pda_amount (int): The number of tokens to transfer to the recipient's PDA account.
        ata_amount (int): The number of tokens to transfer to the recipient's ATA account.
        approve_ata_amount (int): The number of tokens to approve for delegate contract address.

        Returns: None

        Example:
            >> recipient = NeonUser(...)  # must have 'checksum_address' and 'solana_account'
            >> self.pop_up_balance(recipient, 1000, 500)
        # This transfers 1000 tokens to the recipient's PDA and 500 tokens to their ATA.
        """

        if pda_amount:
            self.transfer(self.owner, recipient.checksum_address, pda_amount)  # PDA top up

        if ata_amount is not None:
            ata_account = evm_loader.create_associate_token_acc(
                recipient.solana_account, recipient.solana_account, self.token_mint_pubkey
            )
            solana_contract_account = evm_loader.ether2program(self.contract.address)

            trx = Transaction()
            approve_ata_amount = approve_ata_amount or ata_amount
            trx.add(
                approve(
                    ApproveParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=ata_account,
                        delegate=solana_contract_account,
                        owner=recipient.solana_account.pubkey(),
                        amount=approve_ata_amount,
                    )
                )
            )
            evm_loader.send_tx_and_check_status_ok(trx, recipient.solana_account)

            self.transfer_solana(self.owner, bytes(ata_account), ata_amount)
