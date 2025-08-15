import pytest

from integration.tests.basic.helpers.chains import make_nonce_the_biggest_for_chain
from utils.erc20wrapper import ERC20Wrapper


@pytest.fixture(scope="class")
def counter_contract_two_chain(account_with_all_tokens, client_and_price, web3_client_sol, web3_client):
    w3_client, _ = client_and_price
    make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
    contract, _ = w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=account_with_all_tokens)
    return contract


@pytest.fixture(scope="class", params=["neon", "sol"])
def client_and_price(web3_client, web3_client_sol, request, environment):
    client = {
        "neon": web3_client,
        "sol": web3_client_sol if "sol" in environment.network_ids else None,
    }.get(request.param)

    if client:
        price = client.get_token_usd_gas_price()
        return client, price
    pytest.skip(f"{request.param} chain is not available")


@pytest.fixture(scope="class")
def erc20_wrapper(
    account_with_all_tokens,
    client_and_price,
    faucet,
    solana_account,
    sol_client,
    web3_client_sol,
    web3_client,
) -> ERC20Wrapper:
    client, _ = client_and_price
    make_nonce_the_biggest_for_chain(account_with_all_tokens, client, [web3_client, web3_client_sol])
    contract = ERC20Wrapper(
        client,
        faucet,
        "Test AAA",
        "AAA",
        sol_client,
        owner=account_with_all_tokens,
        solana_account=solana_account,
        mintable=True,
    )
    contract.mint_tokens(account_with_all_tokens, contract.owner.address)
    return contract


@pytest.fixture(scope="class")
def mapping_actions_contract(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Common", version="0.8.19", contract_name="MappingActions", account=accounts[0]
    )
    return contract


@pytest.fixture(scope="class")
def increase_storage_contract(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/IncreaseStorage",
        version="0.8.10",
        account=accounts[0],
    )
    return contract
