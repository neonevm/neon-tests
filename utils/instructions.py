import hashlib
import json

import base58
from solana.publickey import PublicKey
from solana.system_program import SYS_PROGRAM_ID
from solana.transaction import AccountMeta, TransactionInstruction
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID

COMPUTE_BUDGET_ID: PublicKey = PublicKey(
    "ComputeBudget111111111111111111111111111111")
DEFAULT_UNITS = 500 * 1000
DEFAULT_HEAP_FRAME = 256 * 1024


class Instruction:
    @staticmethod
    def balance_account(solana_wallet, account_pubkey, contract_pubkey,
                   neon_wallet, evm_loader_id, chain_id) -> TransactionInstruction:

        keys = [
            AccountMeta(pubkey=solana_wallet,
                        is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROGRAM_ID,
                        is_signer=False, is_writable=False),
            AccountMeta(pubkey=account_pubkey,
                        is_signer=False, is_writable=True),
            AccountMeta(pubkey=contract_pubkey,
                        is_signer=False, is_writable=True),
        ]

        data = bytes.fromhex('2D') + bytes.fromhex(str(neon_wallet)[2:])  + chain_id.to_bytes(8, 'little')
        return TransactionInstruction(
            program_id=PublicKey(evm_loader_id),
            keys=keys,
            data=data)

    @staticmethod
    def sync_native(account: PublicKey):
        keys = [AccountMeta(pubkey=account, is_signer=False, is_writable=True)]
        data = bytes.fromhex('11')
        return TransactionInstruction(keys=keys, program_id=TOKEN_PROGRAM_ID, data=data)

    @staticmethod
    def deposit(
            ether_address: bytes,
            chain_id: int,
            balance_account: PublicKey,
            contract_account: PublicKey,
            mint: PublicKey,
            source: PublicKey,
            pool: PublicKey,
            operator_pubkey: PublicKey,
            evm_loader_id
    ) -> TransactionInstruction:
        data = bytes.fromhex('27') + ether_address + chain_id.to_bytes(8, 'little')
        accounts = [
            AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=source, is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
            AccountMeta(pubkey=balance_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=contract_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=operator_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]
        return TransactionInstruction(program_id=PublicKey(evm_loader_id), data=data, keys=accounts)

    @staticmethod
    def compute_budget_utils(operator, units=DEFAULT_UNITS) -> TransactionInstruction:
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(PublicKey(operator.public_key),
                              is_signer=True, is_writable=False)],
            data=bytes.fromhex("02") + units.to_bytes(4, "little")
        )

    @staticmethod
    def request_heap_frame(operator, heap_frame=DEFAULT_HEAP_FRAME) -> TransactionInstruction:
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(PublicKey(operator.public_key),
                              is_signer=True, is_writable=False)],
            data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )

    @staticmethod
    def associated_token_account(
            payer: PublicKey,
            associated_token: PublicKey,
            owner: PublicKey,
            mint: PublicKey,
            instruction_data: bytes,
            programId=TOKEN_PROGRAM_ID,
            associatedTokenProgramId=ASSOCIATED_TOKEN_PROGRAM_ID) -> TransactionInstruction:
        keys = [
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=associated_token,
                        is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYS_PROGRAM_ID,
                        is_signer=False, is_writable=False),
            AccountMeta(pubkey=programId, is_signer=False, is_writable=False),
        ]

        return TransactionInstruction(
            keys=keys,
            program_id=associatedTokenProgramId,
            data=instruction_data
        )

    @staticmethod
    def claim(_from, to, amount, web3_client, ata_address,
              emulate_signer, contract, gas_price=None):
        emulated_tx = None
        result = dict()

        claim_to = contract.contract.functions.claimTo(
            bytes(ata_address), _from.address, amount)
        data = claim_to.abi

        tx = {
            "from": _from.address,
            "to": to,
            "nonce": web3_client.eth.get_transaction_count(emulate_signer.address),
            "gasPrice": gas_price if gas_price is not None else web3_client.gas_price(),
            "chainId": web3_client.eth.chain_id,
            "data": json.dumps(data).encode('utf-8'),
            "gas": 100000000
        }

        signed_tx = web3_client._web3.eth.account.sign_transaction(
            tx, _from.key)
        if signed_tx.rawTransaction is not None:
            emulated_tx = web3_client.get_neon_emulate(
                str(signed_tx.rawTransaction.hex())[2:])
        if emulated_tx is not None:
            for account in emulated_tx['result']['solana_accounts']:
                key = account['pubkey']
                result[key] = AccountMeta(pubkey=PublicKey(
                    key), is_signer=False, is_writable=True)
                if 'contract' in account:
                    key = account['contract']
                    result[key] = AccountMeta(pubkey=PublicKey(
                        key), is_signer=False, is_writable=True)

            for account in emulated_tx['result']['solana_accounts']:
                key = account['pubkey']
                result[key] = AccountMeta(pubkey=PublicKey(
                    key), is_signer=False, is_writable=True)

        return signed_tx, result

    @staticmethod
    def build_tx_instruction(solana_wallet, neon_wallet, neon_raw_transaction,
                            neon_keys, evm_loader_id):
        program_id = PublicKey(evm_loader_id)
        treasure_pool_index = 2
        treasure_pool_address = get_collateral_pool_address(
            treasure_pool_index, evm_loader_id)

        data = bytes.fromhex('1f') + treasure_pool_index.to_bytes(4, 'little') + \
               bytes.fromhex(str(neon_raw_transaction.hex())[2:])
        keys = [AccountMeta(pubkey=solana_wallet, is_signer=True, is_writable=True),
                AccountMeta(pubkey=treasure_pool_address,
                            is_signer=False, is_writable=True),
                AccountMeta(pubkey=neon_wallet,
                            is_signer=False, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID,
                            is_signer=False, is_writable=False),
                AccountMeta(pubkey=program_id, is_signer=False,
                            is_writable=False),
                ]

        for k in neon_keys:
            keys.append(neon_keys[k])

        return TransactionInstruction(
            keys=keys,
            program_id=program_id,
            data=data
        )


def get_collateral_pool_address(index: int, evm_loader_id):
    return PublicKey.find_program_address(
        [bytes('treasury_pool', 'utf8'), index.to_bytes(4, 'little')],
        PublicKey(evm_loader_id)
    )[0]


def get_solana_wallet_signer(solana_account, neon_account, web3_client):
    solana_wallet = base58.b58encode(str(solana_account.public_key))
    neon_wallet = bytes(neon_account.address, 'utf-8')
    new_wallet = hashlib.sha256(solana_wallet + neon_wallet).hexdigest()
    emulate_signer_private_key = f'0x{new_wallet}'
    return web3_client.eth.account.from_key(emulate_signer_private_key)
