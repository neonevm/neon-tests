import pytest
from solders.pubkey import Pubkey
from web3.contract import Contract
from utils import helpers
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient
from utils.web3client import Web3Client

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"


@pytest.fixture(scope="class")
def precompiled_contract(web3_client, faucet, accounts):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "precompiled/CommonCaller", "0.8.10", accounts[0]
    )
    return contract


@pytest.fixture(scope="class")
def metaplex_caller(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/MetaplexCaller", "0.8.10", account=accounts[0], contract_name="MetaplexCaller"
    )
    return contract


@pytest.fixture(scope="class")
def metaplex(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/Metaplex", "0.8.10", contract_name="Metaplex")
    contract = web3_client.eth.contract(address=METAPLEX_ADDRESS, abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/SPLToken", "0.8.10")
    contract = web3_client.eth.contract(address=SPL_TOKEN_ADDRESS, abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token_caller(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/SplTokenCaller", "0.8.10", account=accounts[0], contract_name="SplTokenCaller"
    )
    return contract


@pytest.fixture(scope="class")
def blockhash_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/BlockHash",
        "0.8.10",
        contract_name="BlockHashTest",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="class")
def query_account_caller_contract(
        web3_client: Web3Client,
        accounts: EthAccounts,
) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/QueryAccountCaller.sol",
        "0.8.10",
        contract_name="QueryAccountCaller",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="session")
def max_non_existent_solana_address(
        sol_client_session: SolanaClient,
) -> int:
    address_uint_256 = 2 ** 256
    address_exists = True

    while address_exists:
        address_uint_256 -= 1
        pubkey = Pubkey(address_uint_256.to_bytes(32, byteorder='big'))
        address_exists = sol_client_session.get_account_info(pubkey=pubkey).value is not None

    return address_uint_256
