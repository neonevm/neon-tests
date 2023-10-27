from solana.publickey import PublicKey
from solana.system_program import TransferParams, transfer
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (ApproveParams, approve,
                                    get_associated_token_address)

from utils.instructions import Instruction, get_solana_wallet_signer


def neon_from_solana_to_neon_tx(solana_account, neon_wallet, neon_mint, neon_account,
                                amount, evm_loader_id, chain_id):
    '''Transfer NEON from solana to neon transaction'''
    tx = Transaction(fee_payer=solana_account.public_key)
    associated_token_address = get_associated_token_address(
        solana_account.public_key, neon_mint)

    tx.add(approve(
        ApproveParams(
            program_id=TOKEN_PROGRAM_ID,
            source=associated_token_address,
            delegate=neon_wallet,
            owner=solana_account.public_key,
            amount=amount)))

    authority_pool = get_authority_pool_address(
        evm_loader_id)

    pool = get_associated_token_address(authority_pool, neon_mint)

    tx.add(Instruction.deposit(
        bytes.fromhex(neon_account.address[2:]),
        chain_id,
        neon_wallet,
        neon_mint,
        associated_token_address,
        pool,
        solana_account.public_key,
        evm_loader_id))
    return tx


def wSOL_from_solana_to_neon_tx(solana_account, neon_wallet, wSOL_mint, neon_account,
                                amount, evm_loader_id, chain_id):
    '''Transfer wSOL from solana to neon transaction'''
    tx = Transaction(fee_payer=solana_account.public_key)
    associated_token_address = get_associated_token_address(
        solana_account.public_key, wSOL_mint)
    print(associated_token_address)
    tx.add(approve(
        ApproveParams(
            program_id=TOKEN_PROGRAM_ID,
            source=associated_token_address,
            delegate=neon_wallet,
            owner=solana_account.public_key,
            amount=amount)))

    authority_pool = get_authority_pool_address(
        evm_loader_id)

    associated_token_address = get_associated_token_address(
        solana_account.public_key, wSOL_mint)
    pool = get_associated_token_address(authority_pool, wSOL_mint)

    tx.add(Instruction.deposit(
        bytes.fromhex(neon_account.address[2:]),
        chain_id,
        neon_wallet,
        wSOL_mint,
        associated_token_address,
        pool,
        solana_account.public_key,
        evm_loader_id))
    return tx


def wSOL_tx(sol_client, spl_token, amount, solana_wallet, ata_address):
    mint_pubkey = PublicKey(spl_token['address_spl'])
    wSOL_account = sol_client.get_account_info(ata_address).value

    tx = Transaction(fee_payer=solana_wallet)
    if (wSOL_account is None):
        tx.add(Instruction.associated_token_account(
            solana_wallet, ata_address, solana_wallet, mint_pubkey, instruction_data=bytes(0)))
    tx.add(transfer(TransferParams(solana_wallet, ata_address, amount)))
    tx.add(Instruction.sync_native(ata_address))

    return tx


def neon_transfer_tx(web3_client, sol_client, amount, spl_token, solana_account,
                     neon_account, erc20_spl, evm_loader_id):
    chain_id = web3_client._chain_id
    delegate_pda = sol_client.ether2balance(neon_account.address, chain_id, evm_loader_id)

    emulate_signer = get_solana_wallet_signer(
        solana_account, neon_account, web3_client)
    emulated_signer_pda = sol_client.ether2balance(emulate_signer.address, chain_id, evm_loader_id)

    solana_wallet = solana_account.public_key

    ata_address = get_associated_token_address(
        solana_wallet, PublicKey(spl_token['address_spl']))

    neon_transaction, neon_keys = Instruction.claim(neon_account,
                                                    spl_token['address'],
                                                    amount,
                                                    web3_client,
                                                    ata_address,
                                                    emulate_signer,
                                                    erc20_spl)
    tx = Transaction(fee_payer=solana_wallet)

    compute_budget_instruction = Instruction.compute_budget_utils(
        solana_account)
    tx.add(compute_budget_instruction)

    heap_frame_instruction = Instruction.request_heap_frame(solana_account)
    tx.add(heap_frame_instruction)

    tx.add(approve(
        ApproveParams(
            program_id=TOKEN_PROGRAM_ID,
            source=ata_address,
            delegate=delegate_pda,
            owner=solana_account.public_key,
            amount=amount)))

    tx.add(Instruction.balance_account(solana_wallet, delegate_pda,
                                       neon_account.address, evm_loader_id, chain_id))

    tx.add(Instruction.balance_account(solana_wallet, emulated_signer_pda,
                                       emulate_signer.address, evm_loader_id, chain_id))

    tx.add(Instruction.build_tx_instruction(solana_wallet, delegate_pda,
                                            neon_transaction.rawTransaction, neon_keys,
                                            evm_loader_id))
    return tx


def get_authority_pool_address(evm_loader_id: str):
    text = 'Deposit'
    return PublicKey.find_program_address([text.encode()], PublicKey(evm_loader_id))[0]
