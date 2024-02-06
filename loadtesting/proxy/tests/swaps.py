import os
import copy
import pathlib
import shutil
import subprocess
import logging
import time
import json
import random

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

    data = {}

    if pathlib.Path("uniswap_contracts.json").is_file():
        LOG.info("File with old contracts exist, load it")
        with open("uniswap_contracts.json", "r") as f:
            data = json.load(f)

    LOG.info("Start deploy Uniswap")
    base_cwd = os.getcwd()
    uniswap_path = pathlib.Path(UNISWAP_TMP_DIR)
    if not uniswap_path.exists():
        LOG.info(f"Clone Uniswap repository to {uniswap_path}")
        shutil.rmtree(UNISWAP_TMP_DIR, ignore_errors=True)
        subprocess.call(f"git clone {UNISWAP_REPO_URL} {uniswap_path}", shell=True)
        os.chdir(uniswap_path)
        subprocess.call("npm install", shell=True)
    os.chdir(uniswap_path)

    sol_client = SolanaClient(environment.credentials["solana_url"])
    neon_client = NeonChainWeb3Client(environment.credentials["proxy_url"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    if "signer" in data and data["signer"]:
        LOG.info("Re-use signer from save data")
        eth_account = neon_client.eth.account.from_key(data["signer"])
    else:
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
    os.chdir(base_cwd)

    if "token_contracts" in data and data["token_contracts"]:
        LOG.info("Load token contracts from saved data")
        solana_account = Keypair.from_secret_key(bytes.fromhex(data["solana_account"]))
        token_contracts["wNEON"] = neon_client.get_deployed_contract(
            data["token_contracts"]["wNEON"], "common/WNeon.sol", "WNEON", "0.4.26"
        )
        for token in ("USDC", "USDT", "tokenA", "tokenB"):
            LOG.info(f"Load token: {token} address: {data['token_contracts'][token]}")
            erc_contract = neon_client.get_deployed_contract(
                data["token_contracts"][token], "EIPs/ERC20/ERC20.sol", "ERC20", "0.8.0"
            )
            token_contracts[token] = erc_contract

        for token in ("USDC_SPL", "USDT_SPL"):
            name = f"Test {token}"

            erc20_wrapper = ERC20Wrapper(
                neon_client,
                faucet,
                name,
                token,
                sol_client,
                solana_account=data["solana_account"],
                account=eth_account,
                mintable=True,
            )
            token_contracts[token] = erc20_wrapper
    else:
        LOG.info("Deploy wNEON token")
        wneon_contract, _ = neon_client.deploy_and_get_contract(
            "common/WNeon.sol", account=eth_account, version="0.4.26", contract_name="WNEON"
        )
        LOG.info(f"wNEON contract address: {wneon_contract.address}")
        instruction_tx = wneon_contract.functions.deposit().build_transaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
                "value": web3.Web3.to_wei(18000, "ether"),
            }
        )
        tx = neon_client.send_transaction(eth_account, instruction_tx)
        LOG.info(f"Deposit wNEON tx: {tx['transactionHash'].hex()}")
        token_contracts["wNEON"] = wneon_contract

        LOG.info("Deploy ERC20 tokens for Uniswap")
        for token in ("USDC", "USDT", "tokenA", "tokenB"):
            erc_contract, _ = neon_client.deploy_and_get_contract(
                "EIPs/ERC20/ERC20.sol",
                account=eth_account,
                version="0.8.0",
                constructor_args=[token, token, web3.Web3.to_wei(10000000, "ether")],
            )
            LOG.info(f"{token} contract address: {erc_contract.address}")
            token_contracts[token] = erc_contract

        LOG.info("Deploy SPL tokens")
        solana_account = Keypair.generate()
        for token in ("USDC_SPL", "USDT_SPL"):
            name = f"Test {token}"

            erc20_wrapper = ERC20Wrapper(
                neon_client,
                faucet,
                name,
                token,
                sol_client,
                solana_account=solana_account,
                account=eth_account,
                mintable=True,
            )
            erc20_wrapper.deploy_wrapper(True)
            erc20_wrapper.mint_tokens(eth_account, eth_account.address, 18446744073709551615)
            token_contracts[token] = erc20_wrapper

    os.chdir(uniswap_path)
    LOG.info("Deploy Uniswap factory")

    if "factory" in data and data["factory"]:
        uniswap2_factory = neon_client.get_deployed_contract(
            data["factory"], str(uniswap_path / "contracts/v2-core/UniswapV2Factory.sol"), solc_version="0.5.16"
        )
    else:
        uniswap2_factory, _ = neon_client.deploy_and_get_contract(
            str(uniswap_path / "contracts/v2-core/UniswapV2Factory.sol"),
            account=eth_account,
            version="0.5.16",
            constructor_args=[eth_account.address],
        )
    LOG.info(f"Factory address: {uniswap2_factory.address}")

    LOG.info("Deploy Uniswap router")

    if "router" in data and data["router"]:
        uniswap2_router = neon_client.get_deployed_contract(
            data["router"],
            str(uniswap_path / "contracts/v2-periphery/UniswapV2Router02.sol"),
            solc_version="0.6.6",
            import_remapping={"@uniswap": str(uniswap_path / "node_modules/@uniswap")},
        )
    else:
        uniswap2_router, _ = neon_client.deploy_and_get_contract(
            str(uniswap_path / "contracts/v2-periphery/UniswapV2Router02.sol"),
            account=eth_account,
            version="0.6.6",
            import_remapping={"@uniswap": str(uniswap_path / "node_modules/@uniswap")},
            constructor_args=[uniswap2_factory.address, token_contracts["wNEON"].address],
        )
    LOG.info(f"Router address: {uniswap2_router.address}")

    LOG.info("Deploy Uniswap pairs")

    pair_contract_interface = helpers.get_contract_interface(
        str(uniswap_path / "contracts/v2-core/UniswapV2Pair.sol"), version="0.5.16"
    )

    if "pair_contracts" in data and data["pair_contracts"]:
        for pair in pair_contracts:
            token1, token2 = pair.split("/")

            token1_addr = (
                token_contracts[token1].contract.address if "SPL" in token1 else token_contracts[token1].address
            )
            token2_addr = (
                token_contracts[token2].contract.address if "SPL" in token2 else token_contracts[token2].address
            )
            pair_address = uniswap2_factory.functions.getPair(token1_addr, token2_addr).call()

            pair_contract = neon_client.eth.contract(address=pair_address, abi=pair_contract_interface["abi"])
            pair_contracts[pair] = pair_contract
    else:
        for pair in pair_contracts:
            LOG.info(f"Deploy pair: {pair}")
            token1, token2 = pair.split("/")

            token1_addr = (
                token_contracts[token1].contract.address if "SPL" in token1 else token_contracts[token1].address
            )
            token2_addr = (
                token_contracts[token2].contract.address if "SPL" in token2 else token_contracts[token2].address
            )

            pair_create_tx = uniswap2_factory.functions.createPair(token1_addr, token2_addr).build_transaction(
                {
                    "from": eth_account.address,
                    "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                    "gasPrice": neon_client.gas_price(),
                }
            )
            tx = neon_client.send_transaction(eth_account, pair_create_tx)
            LOG.info(f"Pair transaction {tx['transactionHash'].hex()}")

            pair_address = uniswap2_factory.functions.getPair(token1_addr, token2_addr).call()

            pair_contract = neon_client.eth.contract(address=pair_address, abi=pair_contract_interface["abi"])
            pair_contracts[pair] = pair_contract
            LOG.info(f"Pair {pair} address: {pair_address}")

        LOG.info("Approve all tokens for router before add liquidity")
        for token in token_contracts:
            c = token_contracts[token]

            if "SPL" in token:
                c = token_contracts[token].contract

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
            token1_addr = (
                token_contracts[token1].contract.address if "SPL" in token1 else token_contracts[token1].address
            )
            token2_addr = (
                token_contracts[token2].contract.address if "SPL" in token2 else token_contracts[token2].address
            )

            token1_amount = web3.Web3.to_wei(2000, "ether")
            token2_amount = web3.Web3.to_wei(2000, "ether")

            if "SPL" in token1:
                token1_amount = web3.Web3.to_wei(2000, "gwei")
            if "SPL" in token2:
                token2_amount = web3.Web3.to_wei(2000, "gwei")

            for t in (token1, token2):
                c = token_contracts[t]
                if "SPL" in t:
                    c = token_contracts[t].contract
                balance = c.functions.balanceOf(eth_account.address).call()
                LOG.info(f"Signer balance for token: {t}: {balance}")

            tr = uniswap2_router.functions.addLiquidity(
                token1_addr,
                token2_addr,
                token1_amount,
                token2_amount,
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
            LOG.info(f"Add liquidity transaction {tx['transactionHash'].hex()}")

        os.chdir(base_cwd)

    data = {
        "signer": eth_account,
        "solana_account": solana_account,
        "router": uniswap2_router,
        "factory": uniswap2_factory,
        "token_contracts": token_contracts,
        "pair_contracts": pair_contracts,
    }

    with open("uniswap_contracts.json", "w") as f:
        saved_data = {
            "signer": eth_account.key.hex(),
            "solana_account": solana_account.secret_key.hex(),
            "router": uniswap2_router.address,
            "factory": uniswap2_factory.address,
            "token_contracts": {k: v.address for k, v in token_contracts.items()},
            "pair_contracts": {k: v.address for k, v in pair_contracts.items()},
        }
        json.dump(saved_data, f, indent=4)
    LOG.info(f"Signer user: {eth_account.address}")
    environment.uniswap = data

    users = {i: neon_client.eth.account.from_key(key) for i, key in data.get("users", {}).items()}
    environment.users = users


@events.test_stopping.add_listener
def save_users(environment: "locust.env.Environment", **kwargs):
    if environment.parsed_options.exclude_tags and "uniswap" in environment.parsed_options.exclude_tags:
        return

    if environment.parsed_options.tags and "uniswap" not in environment.parsed_options.tags:
        return

    with open("uniswap_contracts.json", "w") as f:
        data = json.load(f)

    data["users"] = {i: user.key.hex() for i, user in environment.users.items()}

    with open("uniswap_contracts.json", "w") as f:
        json.dump(data, f, indent=4)


class SwapUser(User):
    def on_start(self):
        """
        1. Receive token from faucet
        2. Receive all tokens
        3. Approve all tokens for router
        """
        LOG.info("Initiate user")
        self.neon_client = NeonChainWeb3Client(self.environment.credentials["proxy_url"])
        faucet = Faucet(self.environment.credentials["faucet_url"], self.neon_client)

        user_count = self.environment.runner.user_count

        if user_count in self.environment.users:
            self.user = self.neon_client.eth.account.from_key(self.environment.users[user_count])
        else:
            self.user = self.neon_client.create_account()
            self.environment.users[user_count] = self.user
        faucet.request_neon(self.user.address, 2000)

        for token in self.environment.uniswap["token_contracts"]:
            LOG.info(f"Approve and get token {token} for user {self.user.address}")
            c = self.environment.uniswap["token_contracts"][token]
            amount = web3.Web3.to_wei(100, "ether")
            if "SPL" in token:
                c = self.environment.uniswap["token_contracts"][token].contract
                amount = web3.Web3.to_wei(10, "gwei")
            LOG.info(f"Approve token {token} for user {self.user.address}")
            tr = c.functions.approve(self.environment.uniswap["router"].address, MAX_UINT_256).build_transaction(
                {
                    "from": self.user.address,
                    "nonce": self.neon_client.eth.get_transaction_count(self.user.address),
                    "gasPrice": self.neon_client.gas_price(),
                }
            )
            LOG.info("Send approve transaction")
            self.neon_client.send_transaction(self.user, tr)

            LOG.info(f"Transfer token {token} for user {self.user.address}")
            LOG.info(
                f"Signer balance for token: {token}: {c.functions.balanceOf(self.environment.uniswap['signer'].address).call()}"
            )
            LOG.info(f"User balance for token: {token}: {c.functions.balanceOf(self.user.address).call()}")
            tr = c.functions.transfer(self.user.address, amount).build_transaction(
                {
                    "from": self.environment.uniswap["signer"].address,
                    "nonce": self.neon_client.eth.get_transaction_count(self.environment.uniswap["signer"].address),
                    "gasPrice": self.neon_client.gas_price(),
                }
            )
            LOG.info("Send transfer transaction")
            self.neon_client.send_transaction(self.environment.uniswap["signer"], tr)
        LOG.info(f"User {self.user.address} initialization success")

    def send_swap_transaction(self, tx, event_name):
        request_meta = {
            "request_type": "swaps",
            "name": event_name,
            "start_time": time.time(),
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        start_perf_counter = time.perf_counter()
        try:
            self.neon_client.send_transaction(self.user, tx)
        except Exception as e:
            request_meta["exception"] = e
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self.environment.events.request.fire(**request_meta)

    @task
    def swap_wneon_usdc(self):
        token1 = self.environment.uniswap["token_contracts"]["wNEON"]
        token2 = self.environment.uniswap["token_contracts"]["USDC"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: wNEON: {token1_balance}, USDC: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap wNEON <-> USDC")

    @task
    def swap_wneon_usdt(self):
        token1 = self.environment.uniswap["token_contracts"]["wNEON"]
        token2 = self.environment.uniswap["token_contracts"]["USDT"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: wNEON: {token1_balance}, USDT: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap wNEON <-> USDT")

    @task
    def swap_usdc_usdt(self):
        token1 = self.environment.uniswap["token_contracts"]["USDC"]
        token2 = self.environment.uniswap["token_contracts"]["USDT"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: USDC: {token1_balance}, USDT: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap USDC <-> USDT")

    @task
    def swap_tokena_tokenb(self):
        token1 = self.environment.uniswap["token_contracts"]["tokenA"]
        token2 = self.environment.uniswap["token_contracts"]["tokenB"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: tokenA: {token1_balance}, tokenB: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap tokenA <-> tokenB")

    @task
    def swap_usdc_spl_usdt_spl(self):
        token1 = self.environment.uniswap["token_contracts"]["USDC_SPL"]
        token2 = self.environment.uniswap["token_contracts"]["USDT_SPL"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: USDC_SPL: {token1_balance}, USDT_SPL: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap USDC_SPL <-> USDT_SPL")

    @task
    def swap_wneon_usdc_spl(self):
        token1 = self.environment.uniswap["token_contracts"]["wNEON"]
        token2 = self.environment.uniswap["token_contracts"]["USDC_SPL"]

        router = self.environment.uniswap["router"]

        token1_balance = token1.functions.balanceOf(self.user.address).call()
        token2_balance = token2.functions.balanceOf(self.user.address).call()
        LOG.info(f"User {self.user.address} balances: wNEON: {token1_balance}, USDC_SPL: {token2_balance}")

        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.to_wei(1, "ether"),
            0,
            random.sample([token1.address, token2.address], 2),
            self.user.address,
            MAX_UINT_256,
        ).build_transaction(
            {
                "from": self.user.address,
                "nonce": self.neon_client.get_nonce(self.user.address),
                "gasPrice": self.neon_client.gas_price(),
            }
        )
        self.send_swap_transaction(swap_trx, "Swap wNEON <-> USDC_SPL")
