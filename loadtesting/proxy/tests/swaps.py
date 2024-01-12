import os
import pathlib
import shutil
import subprocess
import logging
import time

import web3
from locust import tag, task, User, events
from solana.keypair import Keypair

from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient
from utils.faucet import Faucet

from utils import helpers
from utils.erc20wrapper import ERC20Wrapper
from loadtesting.proxy.common import env


LOG = logging.getLogger(__name__)

UNISWAP_REPO_URL = "https://github.com/gigimon/Uniswap-V2-NEON.git"
UNISWAP_TMP_DIR = "/tmp/uniswap-neon"
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


@events.test_start.add_listener
def deploy_uniswap_contracts(environment: "locust.env.Environment", **kwargs):
    """
    Deploy next pairs:
    1. wNEON -> USDC
    2. wNEON -> USDT
    3. USDC -> USDT
    4. tokenA -> tokenB
    5. USDC_SPL -> USDT_SPL
    6. wNEON -> USDC_SPL
    """

    if environment.parsed_options.exclude_tags and "uniswap" in environment.parsed_options.exclude_tags:
        return

    if environment.parsed_options.tags and "uniswap" not in environment.parsed_options.tags:
        return
    LOG.info("Start deploy Uniswap")
    base_cwd = os.getcwd()
    uniswap_path = pathlib.Path(UNISWAP_TMP_DIR)
    if not uniswap_path.exists():
        shutil.rmtree(UNISWAP_TMP_DIR, ignore_errors=True)
        subprocess.call(f"git clone {UNISWAP_REPO_URL} {uniswap_path}", shell=True)
        os.chdir(uniswap_path)
        subprocess.call("npm install", shell=True)
    os.chdir(uniswap_path)

    sol_client = SolanaClient(environment.credentials["solana_url"])
    neon_client = NeonChainWeb3Client(environment.credentials["proxy_url"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 20000)

    token_contracts = {"wNEON": "", "USDC": "", "USDT": "", "USDC_SPL": "", "USDT_SPL": "", "tokenA": "", "tokenB": ""}
    pair_contracts = {
        "wNEON/USDC": "",
        "wNEON/USDT": "",
        "USDC/USDT": "",
        "tokenA/tokenB": "",
        "USDC_SPL/USDT_SPL": "",
        "wNEON/USDC_SPL": "",
    }

    LOG.info("Deploy wNEON token")
    wneon_contract, _ = neon_client.deploy_and_get_contract(
        "common/WNeon.sol",
        account=eth_account,
        version="0.4.26",
    )
    LOG.info(f"wNEON contract address: {wneon_contract.address}")
    instruction_tx = wneon_contract.functions.deposit().build_transaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
            "value": web3.Web3.to_wei(10000, "ether"),
        }
    )
    tx = neon_client.send_transaction(eth_account, instruction_tx)
    LOG.info(f"Deposit wNEON tx: {tx}")
    token_contracts["wNEON"] = wneon_contract

    LOG.info("Deploy ERC20 tokens for Uniswap")
    for token in ("USDC", "USDT", "tokenA", "tokenB"):
        erc_contract, _ = neon_client.deploy_and_get_contract(
            # str(uniswap_path / "contracts/v2-core/test/ERC20.sol"),
            "EIPs/ERC20/ERC20.sol",
            account=eth_account,
            version="0.8.0",
            constructor_args=[token, token, web3.Web3.to_wei(10000000000, "ether")],
        )
        LOG.info(f"{token} contract address: {erc_contract.address}")
        token_contracts[token] = erc_contract

    LOG.info("Deploy SPL tokens")
    for token in ("USDC_SPL", "USDT_SPL"):
        name = f"Test {token}"

        erc20_wrapper = ERC20Wrapper(
            neon_client,
            faucet,
            name,
            token,
            sol_client,
            solana_account=Keypair.generate(),
            account=eth_account,
            mintable=True,
        )
        erc20_wrapper.deploy_wrapper(True)
        erc20_wrapper.mint_tokens(eth_account, eth_account.address, 18446744073709551615)
        token_contracts[token] = erc20_wrapper

    LOG.info("Deploy Uniswap factory")
    uniswap2_factory, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-core/UniswapV2Factory.sol"),
        account=eth_account,
        version="0.5.16",
        constructor_args=[eth_account.address],
    )

    LOG.info("Deploy Uniswap router")
    uniswap2_router, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-periphery/UniswapV2Router02.sol"),
        account=eth_account,
        version="0.6.6",
        import_remapping={"@uniswap": str(uniswap_path / "node_modules/@uniswap")},
        constructor_args=[uniswap2_factory.address, token_contracts["wNEON"].address],
    )

    LOG.info("Deploy Uniswap pairs")

    pair_contract_interface = helpers.get_contract_interface(
        str(uniswap_path / "contracts/v2-core/UniswapV2Pair.sol"), version="0.5.16"
    )

    for pair in pair_contracts:
        LOG.info(f"Deploy pair: {pair}")
        token1, token2 = pair.split("/")

        token1_addr = token_contracts[token1].contract.address if "SPL" in token1 else token1_addr = token_contracts[token1].address
        token2_addr = token_contracts[token2].contract.address if "SPL" in token2 else token2_addr = token_contracts[token2].address

        pair_create_tx = uniswap2_factory.functions.createPair(
            token1_addr, token2_addr
        ).build_transaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
            }
        )
        tx = neon_client.send_transaction(eth_account, pair_create_tx)
        LOG.info(f"Pair transaction {tx}")

        pair_address = uniswap2_factory.functions.getPair(
            token1_addr, token2_addr
        ).call()

        pair_contract = neon_client.eth.contract(address=pair_address, abi=pair_contract_interface["abi"])
        pair_contracts[pair] = pair_contract

    LOG.info("Approve all tokens for router before add liquidity")
    for token in token_contracts:
        c = token_contracts[token]
        tr = c.functions.approve(uniswap2_router.address, MAX_UINT_256).build_transaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
            }
        )
        neon_client.send_transaction(eth_account, tr)

    LOG.info("Add liquidities to pools")
    for pair in pair_contracts:
        LOG.info(f"Add liquidity to pair {pair}")
        token1, token2 = pair.split("/")
        token1_addr = token_contracts[token1].contract.address if "SPL" in token1 else token1_addr = token_contracts[token1].address
        token2_addr = token_contracts[token2].contract.address if "SPL" in token2 else token2_addr = token_contracts[token2].address

        tr = uniswap2_router.functions.addLiquidity(
            token1_addr,
            token2_addr,
            web3.Web3.to_wei(1000, "ether"),
            web3.Web3.to_wei(1000, "ether"),
            0,
            0,
            eth_account.address,
            0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
        ).build_transaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
            }
        )
        tx = neon_client.send_transaction(eth_account, tr)
        LOG.info(f"Add liquidity transaction {tx}")

    os.chdir(base_cwd)
    environment.uniswap = {
        "signer": eth_account,
        "router": uniswap2_router,
        "factory": uniswap2_factory,
        "token_contracts": token_contracts,
        "pair_contracts": pair_contracts
    }
    environment.uniswap.update(token_contracts)


class SwapUser(User):
    def on_start(self):
        pass

    @task
    def swap_wneon_usdc(self):
        pass

    @task
    def swap_wneon_usdt(self):
        pass

    @task
    def swap_usdc_usdt(self):
        pass

    @task
    def swap_tokena_tokenb(self):
        pass

    @task
    def swap_usdc_spl_usdt_spl(self):
        pass

    @task
    def swap_wneon_usdc_spl(self):
        pass
