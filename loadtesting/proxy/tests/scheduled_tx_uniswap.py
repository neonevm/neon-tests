import logging
import os
import math
import threading
import base58

import web3
from solana.rpc import commitment

from deploy.cli.network_manager import NetworkManager
from utils.accounts import EthAccounts
from utils.consts import LAMPORT_PER_SOL, wSOL, REMAPPING_ZEPPELIN_UNISWAP
from utils.erc20wrapper import ERC20NewWrapper
from utils.evm_loader import EvmLoader
from utils.faucet import Faucet
from utils.helpers import decode_function_signature, decode_function_with_stucture_in_arg_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success

from locust import User, tag, task, events, env
from loadtesting.proxy.common.base import NeonProxyTasksSet
from utils.web3client import NeonChainWeb3Client
from solders.keypair import Keypair

LOG = logging.getLogger(__name__)
UNISWAP_USER_LOCK = threading.Lock()

token_mint_amount = web3.Web3.to_wei(1, "ether")
initial_amount = 10_000_000
fee = 500


def get_min_tick(tick_spacing: int) -> int:
    return math.ceil(-887272 / tick_spacing) * tick_spacing


def get_max_tick(tick_spacing: int) -> int:
    return math.floor(887272 / tick_spacing) * tick_spacing

def fund_solana_account(evm_loader, solana_account, bank_account, network, network_object):
    if network != "local" and network_object["use_bank"]:
        evm_loader.send_sol(bank_account, solana_account.pubkey(), int(5 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(
            solana_account.pubkey(), 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed
        )


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

    # create solana account
    solana_account = Keypair()
    fund_solana_account(environment.evm_loader, 
                        solana_account, 
                        bank_account, 
                        network, 
                        network_object)
    environment.solana_account = solana_account

    # create neon accounts
    neon_accounts = []
    for i in range(neon_users):
        neon_solana_account = Keypair()
        LOG.info(f"Creating {i} neon user for uniswap...")
        neon_user = NeonUser(environment.evm_loader.loader_id, keypair=neon_solana_account)
        neon_accounts.append(neon_user)
        fund_solana_account(environment.evm_loader, 
                            neon_user.solana_account, 
                            bank_account, 
                            network, 
                            network_object)

    test_tokens = ["TTA", "TTB", "WETH"]
    tokens = {}

    # deploy erc20 tokens
    for token in test_tokens:
        LOG.info(f"Start to deploy token {token}...")
        eth_account = account_manager.create_account()
        erc20 = ERC20NewWrapper(
            web3_client,
            faucet,
            f"Test {token}",
            token,
            environment.evm_loader,
            solana_account=solana_account,
            mintable=True,
            bank_account=bank_account,
            account=eth_account,
        )
        tokens[f"{token}"] = erc20

        LOG.info("Mint tokens...")
        erc20.mint_tokens(signer=erc20.account, to_address=erc20.account.address, amount=token_mint_amount)

        resp = erc20.mint_tokens(signer=erc20.account, to_address=deployer.address, amount=initial_amount)
        assert resp["status"] == 1

        LOG.info("Mint tokens to neon accounts for swaps...")
        receipts = []
        for neon_user in neon_accounts:
            receipts.append(erc20.mint_tokens(signer=erc20.account, 
                                              to_address=neon_user.checksum_address, 
                                              amount=token_mint_amount))

        for item in receipts:
            assert item["status"] == 1

    LOG.info("Deploy UniswapV3Factory...")
    uniswap_v3_factory, _ = web3_client.deploy_and_get_contract(
        "external/uniswap-v3/contracts/UniswapV3Factory", "0.7.6", account=deployer
    )

    LOG.info("Deploy SwapRouter...")
    swap_router, _ = web3_client.deploy_and_get_contract(
        "external/uniswap-v3/contracts/SwapRouter",
        "0.7.6",
        account=deployer,
        constructor_args=[uniswap_v3_factory.address, tokens["WETH"].contract_address],
        import_remapping=REMAPPING_ZEPPELIN_UNISWAP,
    )

    LOG.info("Approve for swap router...")
    receipts = []
    receipts.append(tokens["TTA"].approve(deployer, swap_router.address, token_mint_amount))
    receipts.append(tokens["TTB"].approve(deployer, swap_router.address, token_mint_amount))
    for item in receipts:
        assert item["status"] == 1

    LOG.info("Create Pool...")
    tx_raw = web3_client.make_raw_tx(deployer)
    tx = uniswap_v3_factory.functions.createPool(
        tokens["TTA"].contract_address, tokens["TTB"].contract_address, fee
    ).build_transaction(tx_raw)
    receipt = web3_client.send_transaction(deployer, tx)
    assert receipt["status"] == 1

    LOG.info("Get Pool...")
    pool_address = uniswap_v3_factory.functions.getPool(
        tokens["TTA"].contract_address, tokens["TTB"].contract_address, fee
    ).call()

    LOG.info("Get deployed pool as UniswapV3Pool...")
    start_price = int(math.sqrt(1 / 2) * (2**96))
    pool = web3_client.get_deployed_contract(
        pool_address,
        contract_name="UniswapV3Pool",
        contract_file="external/uniswap-v3/contracts//UniswapV3Pool",
        solc_version="0.7.6",
        import_remapping=REMAPPING_ZEPPELIN_UNISWAP
    )
    tx_raw = web3_client.make_raw_tx(deployer)
    tx_init_pool = pool.functions.initialize(start_price).build_transaction(tx_raw)
    receipt = web3_client.send_transaction(deployer, tx_init_pool)
    assert receipt["status"] == 1

    LOG.info("Deploy TestUniswapV3Callee...")
    callee, _ = web3_client.deploy_and_get_contract(
        "external/uniswap-v3/contracts/v3-core/test/TestUniswapV3Callee", "0.7.6", account=deployer
    )

    LOG.info("Add Liquidity...")
    receipts = []
    receipts.append(tokens["TTA"].approve(deployer, callee.address, 100 * initial_amount))
    receipts.append(tokens["TTB"].approve(deployer, callee.address, 100 * initial_amount))
    for item in receipts:
        assert item["status"] == 1

    LOG.info("Callee mint...")
    tx_raw = web3_client.make_raw_tx(deployer)
    tx_mint = callee.functions.mint(
        pool.address, deployer.address, get_min_tick(10), get_max_tick(10), int(initial_amount / 10)
    ).build_transaction(tx_raw)
    receipt = web3_client.send_transaction(deployer, tx_mint)
    assert receipt["status"] == 1

    environment.uniswap = {
        "signer": deployer,
        "router": swap_router,
        "factory": uniswap_v3_factory,
        "pool": pool,
        "tokens": tokens,
        "neon_accounts": neon_accounts,
    }


@events.test_stop.add_listener
def teardown(environment: env.Environment, **kwargs):
    network = environment.parsed_options.host
    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)

    if network != "local" and network_object["use_bank"]:
        # Drain SOL for every neon_user
        for neon_user in environment.uniswap["neon_accounts"]:
            environment.evm_loader.drain_sol(neon_user.solana_account, environment.bank_account.pubkey())

        # Drain SOL for solana contract account
        environment.evm_loader.drain_sol(environment.solana_account, environment.bank_account.pubkey())


@tag("scheduled_tx uniswap-v3")
class ScheduledTxsUniswapV3TasksSet(NeonProxyTasksSet):
    """Implements scheduled txs uniswap-v3 task"""
    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

        with UNISWAP_USER_LOCK:
            if not self.user.environment.uniswap["neon_accounts"]:
                raise RuntimeError("Too little users")
            self.uniswap_neon_account = self.user.environment.uniswap["neon_accounts"].pop(0)

    def on_stop(self):
        if self.uniswap_neon_account is not None:
            with UNISWAP_USER_LOCK:
                self.user.environment.uniswap["neon_accounts"].append(self.uniswap_neon_account)
                LOG.info(f"Returned user: {self.uniswap_neon_account.checksum_address}")

    @task
    def task_send_uniswap_scheduled_tx(self):
        """Send scheduled transactions with uniswap-v3 swaps"""
        swap_amount = 10_000
        router = self.user.environment.uniswap["router"]
        token_0 = self.user.environment.uniswap["tokens"]["TTA"]
        token_1 = self.user.environment.uniswap["tokens"]["TTB"]

        if not (token_1.contract_address < token_0.contract_address):
            token_in = token_1
            token_out = token_0
        else:
            token_in = token_0
            token_out = token_1

        self.check_neon_user_balance(self.uniswap_neon_account.solana_account)

        params_input = {
            "tokenIn": token_in.contract_address,
            "tokenOut": token_out.contract_address,
            "fee": fee,
            "recipient": self.uniswap_neon_account.checksum_address,
            "deadline": int(web3.constants.MAX_INT, 16),
            "amountIn": swap_amount,
            "amountOutMinimum": 1,
            "sqrtPriceLimitX96": 1461446703485210103287273052203988822378723970341,
        }

        params_output = {
            "tokenIn": token_in.contract_address,
            "tokenOut": token_out.contract_address,
            "fee": fee,
            "recipient": self.uniswap_neon_account.checksum_address,
            "deadline": int(web3.constants.MAX_INT, 16),
            "amountOut": swap_amount,
            "amountInMaximum": int(web3.constants.MAX_INT, 16),
            "sqrtPriceLimitX96": 1461446703485210103287273052203988822378723970341,
        }

        data = decode_function_signature("approve(address,uint256)", [router.address, 10*swap_amount])
        data_0 = decode_function_with_stucture_in_arg_signature(
            "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))",
                                           [params_input["tokenIn"],
                                            params_input["tokenOut"],
                                            params_input["fee"],
                                            params_input["recipient"],
                                            params_input["deadline"],
                                            params_input["amountIn"],
                                            params_input["amountOutMinimum"],
                                            params_input["sqrtPriceLimitX96"]])
        data_1 = decode_function_with_stucture_in_arg_signature(
            "exactOutputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))", 
                                            [params_output["tokenIn"],
                                            params_output["tokenOut"],
                                            params_output["fee"],
                                            params_output["recipient"],
                                            params_output["deadline"],
                                            params_output["amountOut"],
                                            params_output["amountInMaximum"],
                                            params_output["sqrtPriceLimitX96"]])

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            self.uniswap_neon_account.checksum_address, token_in.contract_address, data, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            self.uniswap_neon_account.checksum_address, token_out.contract_address, data, child_transaction="0xFFFF"
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            self.uniswap_neon_account.checksum_address, router.address, data_0, child_transaction=hex(3)
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            self.uniswap_neon_account.checksum_address, router.address, data_1, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = self.web3_client_sol.estimate_scheduled(self.uniswap_neon_account.solana_account.pubkey(), trx_estimate_obj_list)

        gas_list_new = []
        for i in estimate_result["gasList"]:
            new_value = 10 * int(i, 16)
            gas_list_new.append(hex(new_value))
        estimate_result["gasList"] = gas_list_new

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 2, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 0)

        self.evm_loader.create_tree_account_multiple(self.uniswap_neon_account, 
                                                     self.treasury_pool, 
                                                     tree_acc_data.data, 
                                                     wSOL["address_spl"])
        self.web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(self.web3_client_sol, self.evm_loader, trx.hash().hex(), timeout=180)


class ScheduledTxUser(User):
    tasks = {
        ScheduledTxsUniswapV3TasksSet: 1,
    }
