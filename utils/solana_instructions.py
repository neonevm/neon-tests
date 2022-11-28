from hashlib import sha256

from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import TransactionInstruction, AccountMeta
import solana.system_program as sp


def create_holder_account_instruction(account, operator, evm_loader: PublicKey):
    return TransactionInstruction(
        keys=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
        program_id=evm_loader,
        data=bytes.fromhex("24")
    )


def write_holder_instruction(operator: PublicKey, holder_account: PublicKey, hash: bytes, offset: int,
                             payload: bytes, evm_loader: PublicKey):
    data = (
            bytes.fromhex("26")
            + hash
            + offset.to_bytes(8, byteorder="little")
            + payload
    )
    return TransactionInstruction(
        program_id=evm_loader,
        data=data,
        keys=[
            AccountMeta(pubkey=holder_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ])


def delete_holder_instruction(del_key: PublicKey, acc: Keypair, signer: Keypair, evm_loader: PublicKey):
    return TransactionInstruction(
        program_id=evm_loader,
        data=bytes.fromhex("25"),
        keys=[
            AccountMeta(pubkey=del_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=acc.public_key, is_signer=(signer == acc), is_writable=True),
        ])


def create_account_with_seed_instruction(funding, base, seed, lamports, space, program_id: PublicKey):
    created = PublicKey(sha256(bytes(base) + bytes(seed, 'utf8') + bytes(program_id)).digest())
    return sp.create_account_with_seed(sp.CreateAccountWithSeedParams(
        from_pubkey=funding,
        new_account_pubkey=created,
        base_pubkey=base,
        seed=seed,
        lamports=lamports,
        space=space,
        program_id=program_id
    ))
