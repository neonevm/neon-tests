import pytest


@pytest.fixture(scope="session")
def precompiled_contract(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)

    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "precompiled", "0.8.10", acc, contract_name="TestPrecompiledContracts"
    )
    return acc, contract
