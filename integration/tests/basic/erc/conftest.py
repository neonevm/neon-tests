from typing import Generator

import pytest
from _pytest.config import Config
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)

from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="function")
def solana_associated_token_mintable_erc20(
    erc20_spl_mintable, sol_client, solana_account: Keypair
) -> Generator[tuple[Keypair, Pubkey, Pubkey], None, None]:
    token_mint = erc20_spl_mintable.token_mint_pubkey
    trx = Transaction()
    trx.add(create_associated_token_account(solana_account.pubkey(), solana_account.pubkey(), token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, solana_account, opts=opts)
    solana_address = get_associated_token_address(solana_account.pubkey(), token_mint)
    yield solana_account, token_mint, solana_address


@pytest.fixture(scope="function")
def solana_associated_token_erc20(
    erc20_spl, sol_client, solana_account: Keypair
) -> Generator[tuple[Keypair, Pubkey, Pubkey], None, None]:
    token_mint = erc20_spl.token_mint.pubkey
    trx = Transaction()
    trx.add(create_associated_token_account(solana_account.pubkey(), solana_account.pubkey(), token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, solana_account, opts=opts)
    solana_address = get_associated_token_address(solana_account.pubkey(), token_mint)
    yield solana_account, token_mint, solana_address


@pytest.fixture(scope="class")
def erc721(web3_client_session: NeonChainWeb3Client, faucet, pytestconfig: Config) -> ERC721ForMetaplex:
    return ERC721ForMetaplex(web3_client_session, faucet)


@pytest.fixture(scope="class")
def nft_receiver(web3_client_session, faucet, accounts):
    contract, contract_deploy_tx = web3_client_session.deploy_and_get_contract(
        "EIPs/ERC721/ERC721Receiver", "0.8.10", accounts[0], contract_name="ERC721Receiver"
    )
    return contract


@pytest.fixture(scope="class")
def invalid_nft_receiver(web3_client_session, faucet, accounts):
    contract, contract_deploy_tx = web3_client_session.deploy_and_get_contract(
        "EIPs/ERC721/ERC721InvalidReceiver", "0.8.10", accounts[0], contract_name="ERC721Receiver"
    )
    return contract
