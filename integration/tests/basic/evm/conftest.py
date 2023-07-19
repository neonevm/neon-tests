import pytest

from utils import helpers

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"


@pytest.fixture(scope="class")
def metaplex_caller(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "metaplex_caller.sol", "0.8.10", account=class_account, contract_name="metaplexCaller"
    )
    return contract


@pytest.fixture(scope="class")
def metaplex(web3_client):
    contract_interface = helpers.get_contract_interface("Metaplex", "0.8.10",
                                                        contract_name="Metaplex")
    contract = web3_client.eth.contract(address=METAPLEX_ADDRESS,
                                        abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token(web3_client):
    contract_interface = helpers.get_contract_interface("SPLToken", "0.8.10")
    contract = web3_client.eth.contract(address=SPL_TOKEN_ADDRESS,
                                        abi=contract_interface["abi"])
    return contract

@pytest.fixture(scope="class")
def spl_token_caller(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "spl_token_caller.sol", "0.8.10", account=class_account, contract_name="splTokenCaller"
    )
    return contract
