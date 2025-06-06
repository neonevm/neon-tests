import sys
from unittest.mock import MagicMock
import logging
import os
import threading
import base58
import web3
from deploy.cli.network_manager import NetworkManager
from utils.accounts import EthAccounts
from utils.consts import REMAPPING_ZEPPELIN
from utils.evm_loader import EvmLoader
from utils.faucet import Faucet
from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from locust import User, tag, task, events, env
from loadtesting.proxy.common.base import NeonProxyTasksSet
from utils.solana_client import fund_solana_account
from utils.web3client import NeonChainWeb3Client
from solders.keypair import Keypair

# Mock trio completely before httpcore tries to import it
sys.modules["trio"] = MagicMock()
sys.modules["trio._core"] = MagicMock()
sys.modules["trio._core._run"] = MagicMock()

LOG = logging.getLogger(__name__)
CURVE_USER_LOCK = threading.Lock()

token_mint_amount = web3.Web3.to_wei(1, "ether")


@events.test_start.add_listener
def prepare_contracts(environment: env.Environment, **kwargs):
    neon_users = environment.parsed_options.num_users
    network = environment.parsed_options.host

    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)
    web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
    faucet = Faucet(faucet_url=network_object["faucet_url"], web3_client=web3_client)

    # set bank account if needed
    bank_account = None
    if network != "local" and network_object["use_bank"]:
        if network == "devnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY")
        else:
            raise ValueError("set BANK_PRIVATE_KEY env variable")
        key = base58.b58decode(private_key)
        bank_account = Keypair.from_bytes(key)

    account_manager = EthAccounts(web3_client, faucet, bank_account)
    deployer = account_manager.create_account()

    environment.evm_loader = EvmLoader(
        program_id=network_object["evm_loader"],
        endpoint=network_object["solana_url"],
        neon_chain_id=network_object["network_ids"]["neon"],
        sol_chain_id=network_object["network_ids"]["sol"],
        neon_token_mint_str=network_object["spl_neon_mint"],
    )

    # create neon accounts
    neon_accounts = []
    for i in range(neon_users):
        LOG.info(f"Creating {i} neon user for curve...")
        neon_user = NeonUser(environment.evm_loader.loader_id)
        neon_accounts.append(neon_user)
        fund_solana_account(environment.evm_loader, neon_user.solana_account, bank_account, network)

    test_coins = {
        "renBTC": ("Coin renBTC", "renBTC", 9, deployer.address),
        "wBTC": ("Coin wBTC", "wBTC", 9, deployer.address),
        "sBTC": ("Coin sBTC", "sBTC", 9, deployer.address),
    }
    coins = {}

    # deploy curve tokens
    # TODO Make separate class Coin(Token) with trx not to duplicate code
    for name, params in test_coins.items():
        LOG.info(f"Start to deploy coin {name}...")
        coin, _ = web3_client.deploy_and_get_contract(
            "curve/NeonErc20ForSpl",
            version="0.8.28",
            account=deployer,
            constructor_args=[*params],
            import_remapping=REMAPPING_ZEPPELIN,
        )

        tx = web3_client.make_raw_tx(deployer.address)
        instruction_tx = coin.functions.set_exchange_rate(1).build_transaction(tx)
        resp = web3_client.send_transaction(deployer, instruction_tx)
        assert resp["status"] == 1, "Set exchange rate failed"

        LOG.info("Mint coins to contracts...")
        tx = web3_client.make_raw_tx(deployer.address)
        instruction_tx = coin.functions.mint(deployer.address, token_mint_amount).build_transaction(tx)
        resp = web3_client.send_transaction(deployer, instruction_tx)
        assert resp["status"] == 1, "Mint failed"

        coins[name] = coin

    LOG.info("Mint coins to neon accounts for swaps...")
    for neon_user in neon_accounts:
        for coin in coins.values():
            tx = web3_client.make_raw_tx(deployer.address)
            instruction_tx = coin.functions.mint(neon_user.checksum_address, token_mint_amount).build_transaction(tx)
            receipt = web3_client.send_transaction(deployer, instruction_tx)
            assert receipt["status"] == 1

    # deploy token
    token = web3_client.deploy_compiled_contract(
        deployer,
        "CurveTokenV1",
        [
            "Curve.fi",  # _name: String[64]
            "crvRenWSBTC",  # _symbol: String[32]
            18,  # _decimals: uint256
            0,  # _supply: uint256
        ],
    )

    # deploy pool
    LOG.info("Create Pool...")
    pool = web3_client.deploy_compiled_contract(
        deployer,
        "StableSwapSBTC",
        [
            [
                coins["renBTC"].address,
                coins["wBTC"].address,
                coins["sBTC"].address,
            ],  # _coins: address[N_COINS],
            token.address,  # _pool_token: address,
            200,  # _A: uint256,
            4000000,  # _fee: uint256,
        ],
    )
    tx = web3_client.make_raw_tx(deployer.address)
    instruction_tx = token.functions.set_minter(pool.address).build_transaction(tx)
    resp = web3_client.send_transaction(deployer, instruction_tx)
    assert resp["status"] == 1, "Minter setting failed"

    for name, coin in coins.items():
        LOG.info(f"Coin {name} approve for pool spender")
        tx = web3_client.make_raw_tx(deployer.address)
        instruction_tx = coin.functions.approve(pool.address, token_mint_amount).build_transaction(tx)
        resp = web3_client.send_transaction(deployer, instruction_tx)
        assert resp["status"] == 1, "Approve failed"

    LOG.info("Add Liquidity...")
    tx = web3_client.make_raw_tx(deployer.address)
    instruction_tx = pool.functions.add_liquidity(
        [token_mint_amount, token_mint_amount, token_mint_amount], 0
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(deployer, instruction_tx)
    assert receipt["status"] == 1, "Liquidity adding failed"

    environment.curve = {
        "signer": deployer,
        "pool": pool,
        "coins": coins,
        "token": token,
        "neon_accounts": neon_accounts,
    }


@events.test_stop.add_listener
def teardown(environment: env.Environment, **kwargs):
    network = environment.parsed_options.host
    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)

    if network != "local" and network_object["use_bank"]:
        # Drain SOL for every neon_user
        for neon_user in environment.curve["neon_accounts"]:
            environment.evm_loader.drain_sol(neon_user.solana_account, environment.bank_account.pubkey())

        # Drain SOL for solana contract account
        environment.evm_loader.drain_sol(environment.solana_account, environment.bank_account.pubkey())


@tag("scheduled_tx curve")
class ScheduledTxsCurveTasksSet(NeonProxyTasksSet):
    """Implements scheduled txs curve task"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

        with CURVE_USER_LOCK:
            if not self.user.environment.curve["neon_accounts"]:
                raise RuntimeError("Too little users")
            self.curve_neon_account = self.user.environment.curve["neon_accounts"].pop(0)

    def on_stop(self):
        if self.curve_neon_account is not None:
            with CURVE_USER_LOCK:
                self.user.environment.curve["neon_accounts"].append(self.curve_neon_account)
                LOG.info(f"Returned user: {self.curve_neon_account.checksum_address}")

    @task
    def task_send_curve_scheduled_tx(self):
        """Send scheduled transactions with curve swaps"""
        swap_amount = 10
        pool = self.user.environment.curve["pool"]
        coin_0 = self.user.environment.curve["coins"]["renBTC"]
        coin_1 = self.user.environment.curve["coins"]["wBTC"]

        self.check_solana_balance(self.curve_neon_account.solana_account.pubkey())

        data = decode_function_signature("approve(address,uint256)", [pool.address, swap_amount * 2])

        data_0 = decode_function_signature(
            "exchange(int128,int128,uint256,uint256)",
            [0, 1, swap_amount, 0],
        )

        data_1 = decode_function_signature(
            "exchange(int128,int128,uint256,uint256)",
            [1, 0, swap_amount, 0],
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            self.curve_neon_account.checksum_address, coin_0.address, data, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            self.curve_neon_account.checksum_address, coin_1.address, data, child_transaction=hex(3)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            self.curve_neon_account.checksum_address, pool.address, data_0, child_transaction="0xFFFF"
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            self.curve_neon_account.checksum_address, pool.address, data_1, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = self.web3_client_sol.estimate_scheduled(
            self.curve_neon_account.solana_account.pubkey(), trx_estimate_obj_list
        )

        gas_list_new = []
        for i in estimate_result["gasList"]:
            new_value = 15 * int(i, 16)
            gas_list_new.append(hex(new_value))
        estimate_result["gasList"] = gas_list_new

        trxs = []
        for i, trx_obj in enumerate(trx_estimate_obj_list):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_obj, estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        self.check_solana_balance(self.treasury_pool.account)
        self.evm_loader.create_tree_account_multiple(self.curve_neon_account, self.treasury_pool, tree_acc_data.data)
        self.web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=180)


class ScheduledTxUser(User):
    tasks = {
        ScheduledTxsCurveTasksSet: 1,
    }
