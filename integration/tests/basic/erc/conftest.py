import pytest
from _pytest.config import Config

from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.web3client import NeonChainWeb3Client


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
