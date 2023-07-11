import pytest


@pytest.fixture(scope="class")
def precompiled_contract(web3_client, faucet, class_account):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "precompiled", "0.8.10", class_account, contract_name="TestPrecompiledContracts"
    )
    return contract
