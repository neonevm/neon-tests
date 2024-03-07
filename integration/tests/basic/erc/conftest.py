import random
import string

import pytest
from _pytest.config import Config
from solana.publickey import PublicKey
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)

from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="function")
def solana_associated_token_mintable_erc20(erc20_spl_mintable, sol_client, solana_account):
    token_mint = PublicKey(erc20_spl_mintable.contract.functions.tokenMint().call())
    trx = Transaction()
    trx.add(create_associated_token_account(solana_account.public_key, solana_account.public_key, token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, solana_account, opts=opts)
    solana_address = get_associated_token_address(solana_account.public_key, token_mint)
    yield solana_account, token_mint, solana_address


@pytest.fixture(scope="function")
def solana_associated_token_erc20(erc20_spl, sol_client, solana_account):
    token_mint = erc20_spl.token_mint.pubkey
    trx = Transaction()
    trx.add(create_associated_token_account(solana_account.public_key, solana_account.public_key, token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, solana_account, opts=opts)
    solana_address = get_associated_token_address(solana_account.public_key, token_mint)
    yield solana_account, token_mint, solana_address


@pytest.fixture(scope="class")
def multiple_actions_erc20(web3_client_session, accounts, erc20_spl_mintable):
    contract, contract_deploy_tx = web3_client_session.deploy_and_get_contract(
        "EIPs/ERC20/MultipleActions",
        "0.8.24",
        accounts[0],
        contract_name="MultipleActionsERC20",
        constructor_args=[erc20_spl_mintable.address],
    )
    erc20_spl_mintable.transfer_ownership(erc20_spl_mintable.account, contract.address)
    return accounts[0], contract


@pytest.fixture(scope="class")
def erc721(web3_client_session: NeonChainWeb3Client, faucet, pytestconfig: Config):
    contract = ERC721ForMetaplex(web3_client_session, faucet)
    return contract


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


@pytest.fixture(scope="class")
def multiple_actions_erc721(web3_client_session, faucet, accounts):
    contract, contract_deploy_tx = web3_client_session.deploy_and_get_contract(
        "EIPs/ERC721/MultipleActions", "0.8.10", accounts[0], contract_name="MultipleActionsERC721"
    )
    return accounts[0], contract
