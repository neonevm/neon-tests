import pytest
from utils import helpers

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"


@pytest.fixture(scope="class")
def precompiled_contract(web3_client, faucet, class_account):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "precompiled/CommonCaller", "0.8.10", class_account)
    return contract


@pytest.fixture(scope="class")
def metaplex_caller(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/MetaplexCaller", "0.8.10", account=class_account, contract_name="MetaplexCaller"
    )
    return contract


@pytest.fixture(scope="class")
def metaplex(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/Metaplex", "0.8.10",
                                                        contract_name="Metaplex")
    contract = web3_client.eth.contract(address=METAPLEX_ADDRESS,
                                        abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/SPLToken", "0.8.10")
    contract = web3_client.eth.contract(address=SPL_TOKEN_ADDRESS,
                                        abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token_caller(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/SplTokenCaller", "0.8.10", account=class_account, contract_name="SplTokenCaller"
    )
    return contract


@pytest.fixture(scope="class")
def blockhash_contract(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/BlockHash",
        "0.8.10",
        contract_name="BlockHashTest",
        account=class_account,
    )
    return contract
