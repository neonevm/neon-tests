import pathlib
import struct

import solcx
import spl.token.client
import solana.rpc.api
from solana.rpc.types import TxOpts
from solana.keypair import Keypair
from solana.publickey import PublicKey
import eth_account.signers.local
from construct import Bytes, Int8ul
from construct import Struct
from solana.system_program import SYS_PROGRAM_ID
from solana.rpc.commitment import Commitment
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account
from solana.sysvar import SYSVAR_RENT_PUBKEY
from solana.transaction import Transaction, TransactionInstruction, AccountMeta

from . import web3client


CREATE_ACCOUNT_LAYOUT = Struct(
    "ether" / Bytes(20),
    "nonce" / Int8ul
)


def create_account_layout(ether, nonce):
    return bytes.fromhex("18")+CREATE_ACCOUNT_LAYOUT.build(dict(
        ether=ether,
        nonce=nonce
    ))


class ERC20Wrapper:
    def __init__(self,
                 web3_client: web3client.NeonWeb3Client,
                 sol_client: solana.rpc.api.Client,
                 evm_loader_address,
                 neon_token_mint
                 ):
        self.web3_client = web3_client
        self.sol_client = sol_client
        self.evm_loader = evm_loader_address
        self.neon_token_mint = neon_token_mint

    def eth_to_solana_address(self, eth_account_address: str) -> (PublicKey, int):
        eth_account_addressbytes = bytes.fromhex(eth_account_address[2:])
        return PublicKey.find_program_address([b"\1", eth_account_addressbytes], PublicKey(self.evm_loader))

    def get_wrapped_token_account_address(self, eth_account_address: str, token_mint, erc20_contract_address) -> PublicKey:
        eth_contract_address_bytes = bytes.fromhex(erc20_contract_address[2:])
        eth_account_address_bytes = bytes.fromhex(eth_account_address[2:])
        seeds = [b"\1", b"ERC20Balance",
                 bytes(token_mint),
                 eth_contract_address_bytes,
                 eth_account_address_bytes]
        return PublicKey.find_program_address(seeds, PublicKey(self.evm_loader))[0]

    def is_account_exist(self, acc: PublicKey):
        acc_info_resp = self.sol_client.get_account_info(acc, Commitment("confirmed"))
        if acc_info_resp.get('result', None) is None:
            raise RuntimeError(f'Failed to retrieve account {acc}')

        return not acc_info_resp['result'].get('value', None) is None

    def create_spl(self, owner: Keypair, decimals: int = 9):
        token_mint = spl.token.client.Token.create_mint(
            conn=self.sol_client,
            payer=owner,
            mint_authority=owner.public_key,
            decimals=decimals,
            program_id=TOKEN_PROGRAM_ID
        )

        assoc_addr = token_mint.create_associated_token_account(owner.public_key)

        token_mint.mint_to(
            dest=assoc_addr,
            mint_authority=owner,
            amount=1000000000000000,
            opts=TxOpts(skip_confirmation=False),
        )

        return token_mint

    def deploy_wrapper(self,
                       name, symbol,
                       account: eth_account.signers.local.LocalAccount,
                       mint_address
                       ):
        solcx.install_solc("0.8.10")
        contract_path = (
                pathlib.Path.cwd() / "contracts" / "erc20wrapper.sol"
        ).absolute()

        with open(contract_path, "r") as s:
            source = s.read()

        source = source.replace("Awesome Token", name).replace("AWST", symbol)

        compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10")
        contract_interface = compiled[list(compiled.keys())[0]]

        contract_deploy_tx = self.web3_client.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=[bytes(mint_address)]
        )

        contract = self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

        return contract, contract_deploy_tx["contractAddress"]

    def mint_tokens(self, to_address, solana_owner, mint_address, wrapped_contract, amount: int = 1000000000000000):
        """Mint wrapped tokens to eth user"""
        source_token_acc = get_associated_token_address(solana_owner.public_key, mint_address)
        trx = Transaction()
        neon_acc, nonce = self.eth_to_solana_address(to_address)

        if not self.is_account_exist(neon_acc):
            trx.add(TransactionInstruction(
                program_id=self.evm_loader,
                data=create_account_layout(bytes.fromhex(to_address[2:]), nonce),
                keys=[
                    AccountMeta(pubkey=solana_owner.public_key, is_signer=True, is_writable=True),
                    AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                    AccountMeta(pubkey=neon_acc, is_signer=False, is_writable=True),
                ]))

        dest_token_account = self.get_wrapped_token_account_address(to_address, mint_address, wrapped_contract)
        if not self.is_account_exist(dest_token_account):
            trx.add(TransactionInstruction(
                program_id=self.evm_loader,
                data=bytes.fromhex('0F'),
                keys=[
                    AccountMeta(pubkey=solana_owner.public_key, is_signer=True, is_writable=True),
                    AccountMeta(pubkey=dest_token_account, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=neon_acc, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=self.eth_to_solana_address(wrapped_contract)[0],
                                is_signer=False, is_writable=True),
                    AccountMeta(pubkey=mint_address, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                    AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
                    AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
                ]
            ))

        trx.add(TransactionInstruction(
            program_id=TOKEN_PROGRAM_ID,
            data=b'\3' + struct.pack('<Q', amount),
            keys=[
                AccountMeta(pubkey=source_token_acc, is_signer=False, is_writable=True),
                AccountMeta(pubkey=dest_token_account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=solana_owner.public_key, is_signer=True, is_writable=False)
            ]
        ))

        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        resp = self.sol_client.send_transaction(trx, solana_owner, opts=opts)
        return resp

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