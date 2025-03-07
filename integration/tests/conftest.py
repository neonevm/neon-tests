import inspect
import logging
import os
import random
import string
import time
import typing as tp

import allure
import base58
import pytest
from _pytest.config import Config
from eth_account.signers.local import LocalAccount
from solana.rpc import commitment
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from web3.contract import Contract
from web3.types import TxReceipt

from clickfile import EnvName
from conftest import EnvironmentConfig
from utils.accounts import EthAccounts
from utils.apiclient import JsonRPCSession
from utils.consts import COUNTER_ID, LAMPORT_PER_SOL, MULTITOKEN_MINTS
from utils.erc20 import ERC20
from utils.erc20wrapper import ERC20Wrapper, ERC20NewWrapper
from utils.evm_loader import EvmLoader
from utils.helpers import decode_function_signature, get_selectors
from utils.operator import Operator
from utils.prices import get_sol_price_with_retry
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client, Web3Client
from .basic.helpers.chains import make_nonce_the_biggest_for_chain

log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def ws_subscriber_url(environment: EnvironmentConfig) -> tp.Optional[str]:
    return environment.ws_subscriber_url


@pytest.fixture(scope="session")
def json_rpc_client(environment: EnvironmentConfig) -> JsonRPCSession:
    return JsonRPCSession(environment.proxy_url)


@pytest.fixture(scope="class")
def web3_client(request, web3_client_session) -> tp.Generator[NeonChainWeb3Client, None, None]:
    if inspect.isclass(request.cls):
        request.cls.web3_client = web3_client_session
    yield web3_client_session


@pytest.fixture(scope="class")
def sol_client(request, sol_client_session) -> tp.Generator[SolanaClient, None, None]:
    if inspect.isclass(request.cls):
        request.cls.sol_client = sol_client_session
    yield sol_client_session


@pytest.fixture(scope="session")
def environment(pytestconfig: Config) -> EnvironmentConfig:
    return pytestconfig.environment


@pytest.fixture(scope="session")
def web3_client_sol(environment: EnvironmentConfig) -> tp.Union[Web3Client, None]:
    if "sol" in environment.network_ids:
        return Web3Client(f"{environment.proxy_url}/sol")


@pytest.fixture(scope="session")
def web3_client_usdt(environment: EnvironmentConfig) -> tp.Union[Web3Client, None]:
    if "usdt" in environment.network_ids:
        return Web3Client(f"{environment.proxy_url}/usdt")


@pytest.fixture(scope="session")
def web3_client_eth(environment: EnvironmentConfig) -> tp.Union[Web3Client, None]:
    if "eth" in environment.network_ids:
        return Web3Client(f"{environment.proxy_url}/eth")


@pytest.fixture(scope="session")
def operator(environment: EnvironmentConfig, web3_client_session: NeonChainWeb3Client) -> Operator:
    return Operator(
        environment.proxy_url,
        environment.solana_url,
        environment.spl_neon_mint,
        web3_client_session,
        environment.evm_loader,
    )


@pytest.fixture(scope="session")
def bank_account(pytestconfig: Config) -> tp.Generator[Keypair | None, None, None]:
    account = None
    if pytestconfig.environment.use_bank:
        if pytestconfig.getoption("--network") == "devnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY")
        elif pytestconfig.getoption("--network") == "mainnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY_MAINNET")
        else:
            raise ValueError("set BANK_PRIVATE_KEY or BANK_PRIVATE_KEY_MAINNET env variable")
        key = base58.b58decode(private_key)
        account = Keypair.from_bytes(key)
    yield account


@pytest.fixture(scope="session")
def eth_bank_account(pytestconfig: Config, web3_client_session) -> tp.Generator[Keypair | None, None, None]:
    account = None
    if pytestconfig.environment.eth_bank_account != "":
        account = web3_client_session.eth.account.from_key(pytestconfig.environment.eth_bank_account)
    if pytestconfig.getoption("--network") == "mainnet":
        account = web3_client_session.eth.account.from_key(os.environ.get("ETH_BANK_PRIVATE_KEY_MAINNET"))
    yield account


@pytest.fixture(scope="session")
def solana_account(
    bank_account, environment: EnvironmentConfig, sol_client_session
) -> tp.Generator[Keypair, None, None]:
    account = Keypair()

    if environment.use_bank:
        sol_client_session.send_sol(bank_account, account.pubkey(), int(0.5 * LAMPORT_PER_SOL))
    else:
        sol_client_session.request_airdrop(account.pubkey(), 1 * LAMPORT_PER_SOL)
    yield account

    if environment.use_bank:
        balance = sol_client_session.get_balance(account.pubkey(), commitment=commitment.Confirmed).value
        try:
            sol_client_session.send_sol(account, bank_account.pubkey(), balance - 5000)
        except Exception as e:
            log.info(f"Failed to send sol to bank: {e}")


@pytest.fixture(scope="function")
def new_solana_account(
    bank_account, environment: EnvironmentConfig, sol_client_session
) -> tp.Generator[Keypair, None, None]:
    account = Keypair()
    if environment.use_bank:
        sol_client_session.send_sol(bank_account, account.pubkey(), int(0.01 * LAMPORT_PER_SOL))
    else:
        sol_client_session.request_airdrop(account.pubkey(), 1 * LAMPORT_PER_SOL)
    yield account

    if environment.use_bank:
        balance = sol_client_session.get_balance(account.pubkey(), commitment=commitment.Confirmed).value
        try:
            sol_client_session.send_sol(account, bank_account.pubkey(), balance - 5000)
        except Exception as e:
            log.info(f"Failed to send sol to bank: {e}")


@pytest.fixture(scope="class")
def accounts(request, accounts_session, web3_client_session, pytestconfig: Config, eth_bank_account) -> EthAccounts:
    if inspect.isclass(request.cls):
        request.cls.accounts = accounts_session
    return accounts_session


@pytest.fixture(scope="session")
def erc20_spl(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    environment: EnvironmentConfig,
    sol_client_session,
    solana_account,
    eth_bank_account,
    accounts_session,
) -> tp.Generator[ERC20Wrapper, None, None]:
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=False,
        bank_account=eth_bank_account,
        account=accounts_session[0],
        evm_loader_id=environment.evm_loader,
    )
    erc20.token_mint.approve(
        source=erc20.solana_associated_token_acc,
        delegate=sol_client_session.get_erc_auth_address(
            erc20.account.address,
            erc20.contract.address,
            environment.evm_loader,
        ),
        owner=erc20.solana_acc.pubkey(),
        amount=1000000000000000,
        opts=TxOpts(preflight_commitment=commitment.Confirmed, skip_confirmation=False),
    )

    erc20.claim(erc20.account, bytes(erc20.solana_associated_token_acc), 100000000000000)
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_new(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    environment: EnvironmentConfig,
    sol_client_session,
    solana_account,
    eth_bank_account,
    accounts_session,
) -> tp.Generator[ERC20NewWrapper, tp.Any, tp.Any]:
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20NewWrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=False,
        bank_account=eth_bank_account,
        account=accounts_session[0],
        evm_loader_id=environment.evm_loader,
    )
    erc20.token_mint.approve(
        source=erc20.solana_associated_token_acc,
        delegate=sol_client_session.get_erc_auth_address(
            erc20.account.address,
            erc20.contract.address,
            environment.evm_loader,
        ),
        owner=erc20.solana_acc.pubkey(),
        amount=1000000000000000,
        opts=TxOpts(preflight_commitment=commitment.Confirmed, skip_confirmation=False),
    )

    erc20.claim(erc20.account, bytes(erc20.solana_associated_token_acc), 100000000000000)
    yield erc20


@pytest.fixture(scope="session")
def erc20_simple(web3_client_session, faucet, accounts_session, eth_bank_account) -> tp.Generator[ERC20, None, None]:
    erc20 = ERC20(
        web3_client=web3_client_session, faucet=faucet, bank_account=eth_bank_account, owner=accounts_session[0]
    )
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    sol_client_session,
    solana_account,
    accounts_session,
    eth_bank_account,
) -> tp.Generator[ERC20Wrapper, None, None]:
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=True,
        bank_account=eth_bank_account,
        account=accounts_session[0],
    )
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable_new(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    sol_client_session,
    solana_account,
    accounts_session,
    eth_bank_account,
) -> tp.Generator[ERC20NewWrapper, tp.Any, tp.Any]:
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20NewWrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=True,
        bank_account=eth_bank_account,
        account=accounts_session[0],
    )
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="class")
def class_account_sol_chain(
    evm_loader,
    solana_account,
    web3_client,
    faucet,
    eth_bank_account,
    bank_account,
    environment: EnvironmentConfig,
) -> LocalAccount:
    account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
    if environment.use_bank:
        evm_loader.send_sol(bank_account, solana_account.pubkey(), int(1 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(solana_account.pubkey(), 1 * LAMPORT_PER_SOL)

    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        solana_account,
        account,
        int(1 * LAMPORT_PER_SOL),
    )
    return account


@pytest.fixture(scope="session")
def evm_loader(environment: EnvironmentConfig) -> EvmLoader:
    return EvmLoader(
        program_id=environment.evm_loader,
        endpoint=environment.solana_url,
        neon_chain_id=environment.network_ids["neon"],
        sol_chain_id=environment.network_ids["sol"],
        neon_token_mint_str=environment.spl_neon_mint,
    )


@pytest.fixture(scope="session")
def account_with_all_tokens(
    evm_loader,
    solana_account,
    web3_client_session,
    web3_client_usdt,
    web3_client_eth,
    web3_client_sol,
    environment: EnvironmentConfig,
    faucet,
    eth_bank_account,
    neon_mint,
    operator_keypair,
    evm_loader_keypair,
    bank_account: Keypair | None,
) -> LocalAccount:
    neon_account = web3_client_session.create_account_with_balance(faucet, bank_account=eth_bank_account, amount=500)
    if web3_client_sol:
        lamports = 2 * LAMPORT_PER_SOL
        if environment.use_bank:
            bank_account: Keypair
            evm_loader.send_sol(bank_account, solana_account.pubkey(), lamports)
        else:
            evm_loader.request_airdrop(solana_account.pubkey(), lamports)
        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            solana_account,
            neon_account,
            lamports,
        )
    for client in [web3_client_usdt, web3_client_eth]:
        if client:
            if client == web3_client_usdt:
                mint = MULTITOKEN_MINTS["USDT"]
            else:
                mint = MULTITOKEN_MINTS["ETH"]
            token_mint = Pubkey.from_string(mint)

            evm_loader.mint_spl_to(
                token_mint,
                solana_account,
                1000000000000000,
            )

            evm_loader.sent_token_from_solana_to_neon(
                solana_account,
                token_mint,
                neon_account,
                100000000,
                client.eth.chain_id,
            )
    return neon_account


@pytest.fixture(scope="session")
def neon_mint(environment: EnvironmentConfig) -> Pubkey:
    return Pubkey.from_string(environment.spl_neon_mint)


@pytest.fixture(scope="class")
def withdraw_contract(web3_client, faucet, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract("precompiled/NeonToken", "0.8.10", account=accounts[1])
    return contract


@pytest.fixture(scope="class")
def common_contract(web3_client, accounts, pytestconfig) -> tp.Generator[Contract, None, None]:
    if pytestconfig.getoption("--network") == "mainnet":
        address = os.environ.get("MAINNET_COMMON_CONTRACT_ADDRESS")
        contract = web3_client.get_deployed_contract(address, "common/Common", contract_name="Common")
    else:
        contract, tx = web3_client.deploy_and_get_contract(
            contract="common/Common",
            version="0.8.12",
            contract_name="Common",
            account=accounts[0],
        )
    yield contract


@pytest.fixture(scope="class")
def common_caller_contract(web3_client, accounts, common_contract) -> tp.Generator[Contract, None, None]:
    contract, tx = web3_client.deploy_and_get_contract(
        contract="common/Common",
        version="0.8.12",
        contract_name="CommonCaller",
        account=accounts[0],
        constructor_args=[common_contract.address],
    )
    yield contract


@pytest.fixture(scope="class")
def meta_proxy_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract("./EIPs/MetaProxy", "0.8.10", account=accounts[0])
    return contract


@pytest.fixture(scope="class")
def event_caller_contract(web3_client, accounts) -> tp.Any:
    event_caller, _ = web3_client.deploy_and_get_contract("common/EventCaller", "0.8.12", accounts[0])
    yield event_caller


@pytest.fixture(scope="class")
def event_caller_sol_chain(web3_client_sol, account_with_all_tokens) -> tp.Any:
    event_caller, _ = web3_client_sol.deploy_and_get_contract("common/EventCaller", "0.8.12", account_with_all_tokens)
    yield event_caller


@pytest.fixture(scope="class")
def event_checker_callee_address(web3_client, accounts) -> tp.Any:
    _, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "common/EventsCheckerCallee", "0.8.15", account=accounts[0]
    )
    return contract_deploy_tx["contractAddress"]


@pytest.fixture(scope="class")
def opcodes_checker(web3_client, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/BaseOpCodes", "0.5.16", accounts[0], contract_name="BaseOpCodes"
    )
    return contract


@pytest.fixture(scope="class")
def eip1052_checker(web3_client, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract(
        "EIPs/EIP1052Extcodehash",
        "0.8.10",
        accounts[0],
        contract_name="EIP1052Checker",
    )
    return contract


@pytest.fixture(scope="class")
def wsol(web3_client_sol, class_account_sol_chain) -> Contract:
    contract, _ = web3_client_sol.deploy_and_get_contract(
        contract="common/WNativeChainToken",
        version="0.8.12",
        contract_name="WNativeChainToken",
        account=class_account_sol_chain,
    )
    return contract


@pytest.fixture(scope="class")
def wneon(web3_client, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract(
        "common/WNeon", "0.4.26", account=accounts[0], contract_name="WNEON"
    )
    return contract


@pytest.fixture(scope="class")
def storage_contract(web3_client, accounts) -> tp.Generator[Contract, None, None]:
    contract, _ = web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
        "0.8.8",
        accounts[0],
        contract_name="Storage",
        constructor_args=[],
    )
    yield contract


@pytest.fixture(scope="class")
def storage_contract_with_deploy_tx(web3_client, accounts) -> tp.Generator[tp.Tuple[Contract, TxReceipt], None, None]:
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
        "0.8.8",
        accounts[0],
        contract_name="Storage",
        constructor_args=[],
    )
    yield contract, contract_deploy_tx


@pytest.fixture(scope="class")
def revert_contract(web3_client, accounts) -> tp.Generator[Contract, None, None]:
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Revert",
        version="0.8.10",
        contract_name="TrivialRevert",
        account=accounts[0],
    )
    yield contract


@pytest.fixture(scope="class")
def revert_contract_caller(web3_client, accounts, revert_contract) -> tp.Generator[Contract, None, None]:
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Revert",
        version="0.8.10",
        contract_name="Caller",
        account=accounts[0],
        constructor_args=[revert_contract.address],
    )
    yield contract


@pytest.fixture(scope="session")
def sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    return get_sol_price_with_retry()


@pytest.fixture(scope="session")
def neon_price(web3_client_session) -> float:
    """Get NEON price in usd"""
    price = web3_client_session.get_token_usd_gas_price()
    with allure.step(f"NEON price {price}$"):
        return price


@pytest.fixture(scope="class")
def events_checker_contract(web3_client, accounts) -> tp.Generator[Contract, None, None]:
    contract, _ = web3_client.deploy_and_get_contract("common/EventsCheckerCaller", "0.8.15", account=accounts[0])
    yield contract


@pytest.fixture(scope="class")
def counter_contract(web3_client, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=accounts[0])
    return contract


@pytest.fixture(scope="class")
def counter_contract_sol_chain(web3_client_sol, account_with_all_tokens, web3_client) -> tp.Any:
    make_nonce_the_biggest_for_chain(account_with_all_tokens, web3_client_sol, [web3_client])
    contract, _ = web3_client_sol.deploy_and_get_contract("common/Counter", "0.8.10", account_with_all_tokens)
    yield contract


@pytest.fixture(scope="class")
def nested_call_contracts(accounts, web3_client) -> tp.Generator[tuple[Contract, Contract, Contract], None, None]:
    contract_a, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    contract_b, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="B"
    )
    contract_c, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="C"
    )
    yield contract_a, contract_b, contract_c


@pytest.fixture(scope="function")
def recursion_factory(accounts, web3_client) -> tp.Generator[Contract, None, None]:
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "common/Recursion",
        "0.8.10",
        sender_account,
        contract_name="DeployRecursionFactory",
        constructor_args=[3],
    )
    yield contract


@pytest.fixture(scope="function")
def destroyable_contract(accounts, web3_client) -> tp.Generator[Contract, None, None]:
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/SelfDestroyable", "0.8.10", sender_account, "SelfDestroyable"
    )
    yield contract


@pytest.fixture(scope="class")
def expected_error_checker(accounts, web3_client) -> tp.Generator[Contract, None, None]:
    contract, _ = web3_client.deploy_and_get_contract(
        "common/ExpectedErrorsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    yield contract


@pytest.fixture(scope="class")
def multiple_actions_erc20(web3_client_session, accounts, erc20_spl_mintable):
    contract, contract_deploy_tx = web3_client_session.deploy_and_get_contract(
        "EIPs/ERC20/MultipleActions",
        "0.8.24",
        accounts[0],
        contract_name="MultipleActionsERC20",
        constructor_args=["Test TTT", "TTT", 18],
    )
    return accounts[0], contract


@pytest.fixture(scope="class")
def multiple_actions_erc721(web3_client, accounts):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "EIPs/ERC721/MultipleActions", "0.8.10", accounts[0], contract_name="MultipleActionsERC721"
    )
    return accounts[0], contract


@pytest.fixture(scope="class")
def call_solana_caller(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract("precompiled/CallSolanaCaller.sol", "0.8.10", accounts[0])
    return contract


@pytest.fixture(scope="class")
def counter_resource_address(call_solana_caller, accounts, web3_client) -> tp.Generator[bytes, None, None]:
    tx = web3_client.make_raw_tx(accounts[0].address)
    salt = web3_client.text_to_bytes32("".join(random.choices(string.ascii_letters, k=5)))
    instruction_tx = call_solana_caller.functions.createResource(salt, 8, 100000, bytes(COUNTER_ID)).build_transaction(
        tx
    )
    web3_client.send_transaction(accounts[0], instruction_tx)
    yield call_solana_caller.functions.getResourceAddress(salt).call()


@pytest.fixture(scope="class")
def block_number_contract(web3_client, accounts):
    block_number_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockNumber"
    )
    return block_number_contract, receipt


@pytest.fixture(scope="class")
def block_timestamp_contract(web3_client, accounts):
    block_timestamp_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockTimestamp"
    )
    return block_timestamp_contract, receipt


@pytest.fixture(scope="class")
def eip1559_setup(
    request: pytest.FixtureRequest,
    pytestconfig: Config,
    accounts_session: EthAccounts,
    web3_client_session: NeonChainWeb3Client,
    env_name: EnvName,
):
    """
    Creates type-2 transactions in the db
    """

    # Get the max value of marker @pytest.mark.need_eip1559_blocks(...) among selected tests in the class
    block_count = 1
    selected_tests_in_class = [item for item in request.session.items if item.cls is request.cls]  # noqa
    markers = request.cls.pytestmark + [mark for test in selected_tests_in_class for mark in test.own_markers]
    for marker in markers:
        if marker.name == "need_eip1559_blocks":
            need_eip1559_blocks = marker.args[0]
            block_count = max(block_count, need_eip1559_blocks)

    # Check if the latest blocks already have enough type-2 transactions. If that's the case - return
    fee_history = web3_client_session._web3.eth.fee_history(block_count, "latest", None)  # noqa
    base_fee_per_gas_history = fee_history["baseFeePerGas"]
    if len(base_fee_per_gas_history) >= block_count + 1:
        return

    # Send the transactions
    sender = accounts_session[0]
    recipient = web3_client_session.create_account()
    gas_estimate: tp.Union[int, tp.Literal["auto"]] = "auto"
    value = 10

    for nonce in range(block_count):
        tx_params = web3_client_session.make_raw_tx_eip_1559(
            nonce=nonce,
            chain_id="auto",
            from_=sender.address,
            to=recipient.address,
            value=value,
            gas=gas_estimate,
            max_priority_fee_per_gas="auto",
            max_fee_per_gas="auto",
            access_list=None,
            data=None,
        )

        if gas_estimate == "auto":
            gas_estimate = int(tx_params["gas"])

        start = time.time()
        receipt = web3_client_session.send_transaction(account=sender, transaction=tx_params)
        assert receipt.status == 1

        # Sleep to make sure the next transaction goes to the next block
        min_pause = 3 if env_name is EnvName.GETH else 0.4
        pause = min_pause - (time.time() - start)
        if pause > 0:
            time.sleep(pause)


@pytest.fixture(scope="class")
def diamond_init(web3_client_session, accounts):
    contract, _ = web3_client_session.deploy_and_get_contract(
        "EIPs/EIP2535/upgradeInitializers/DiamondInit.sol",
        "0.8.10",
        accounts[0],
        contract_name="DiamondInit",
    )
    return contract


@pytest.fixture(scope="class")
def facet_cuts(diamond_cut_facet, diamond_loupe_facet, ownership_facet):
    facet_cuts = []
    for facet in [diamond_cut_facet, diamond_loupe_facet, ownership_facet]:
        facet_cuts.append((facet.address, 0, get_selectors(facet.abi)))
    return facet_cuts


@pytest.fixture(scope="class")
def diamond_cut_facet(web3_client_session, accounts):
    contract, _ = web3_client_session.deploy_and_get_contract(
        "EIPs/EIP2535/facets/DiamondCutFacet",
        "0.8.10",
        accounts[0],
        contract_name="DiamondCutFacet",
    )
    return contract


@pytest.fixture(scope="class")
def diamond_loupe_facet(web3_client_session, accounts):
    contract, _ = web3_client_session.deploy_and_get_contract(
        "EIPs/EIP2535/facets/DiamondLoupeFacet.sol",
        "0.8.10",
        accounts[0],
        contract_name="DiamondLoupeFacet",
    )
    return contract


@pytest.fixture(scope="class")
def ownership_facet(web3_client_session, accounts):
    contract, _ = web3_client_session.deploy_and_get_contract(
        "EIPs/EIP2535/facets/OwnershipFacet",
        "0.8.10",
        accounts[0],
        contract_name="OwnershipFacet",
    )
    return contract


@pytest.fixture(scope="class")
def diamond(web3_client_session, diamond_init, facet_cuts, accounts):
    calldata = decode_function_signature("init()")
    diamond_args = [accounts[0].address, diamond_init.address, calldata]
    contract, tx = web3_client_session.deploy_and_get_contract(
        "EIPs/EIP2535/Diamond",
        "0.8.10",
        accounts[0],
        contract_name="Diamond",
        constructor_args=[facet_cuts, diamond_args],
    )
    return contract
