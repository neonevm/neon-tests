import random
import logging

import web3
from gevent import time
from locust import tag, task, User, events

from utils.web3client import NeonWeb3Client
from utils.faucet import Faucet

from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)

ERC20_CONTRACT_NAME = "ERC20.sol"
ERC20_CONTRACT_VERSION = "0.6.6"


@tag("erc20")
class ERC20TasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20TasksSet, self).on_start()
        self._buffer = self.user.environment.shared.erc20_contracts

    @task(1)
    def task_deploy_contract(self):
        """Deploy ERC20 contract"""
        self.log.info(f"Deploy ERC20 contract.")
        amount_range = pow(10, 15)
        amount = random.randint(amount_range, amount_range + pow(10, 3))
        contract, _ = self.deploy_contract(ERC20_CONTRACT_NAME, ERC20_CONTRACT_VERSION, self.account, constructor_args=[amount])
        self._buffer.setdefault(self.account.address, {}).update(
            {contract.address: {"contract": contract, "amount": amount}}
        )

    @task(10)
    def task_send_erc20(self):
        contracts = self._buffer.get(self.account.address)

        if not contracts:
            return

        contract_address = random.choice(list(contracts.keys()))
        contract = contracts[contract_address]["contract"]
        if contracts[contract_address]["amount"] < 1:
            self.log.info(f"low balance on contract: {contracts[contract_address]}, skip transfer")
            del contracts[contract_address]
            return
        recipient = random.choice(self.user.environment.shared.accounts)
        self.log.info(
            f"Send `{ERC20_CONTRACT_NAME}` tokens from contract {str(contract.address)[-8:]} to {str(recipient.address)[-8:]}."
        )
        tx_receipt = self.web3_client.send_erc20(self.account, recipient, 1, contract.address, abi=contract.abi)
        if tx_receipt:
            tx_receipt = dict(tx_receipt)  # AttributeDict -> dict
            tx_receipt["contractAddress"] = contract.address
            self._buffer[self.account.address][contract.address]["amount"] -= 1
            recipient_contracts = self._buffer.get(recipient.address, {})
            recipient_contract = recipient_contracts.get(contract.address, {})
            if not recipient_contract:
                recipient_contract.update({"contract": contract, "amount": 0})
            recipient_contract["amount"] += 1
            self._buffer.setdefault(recipient.address, {}).update({contract.address: recipient_contract})


@events.test_start.add_listener
def prepare_one_contract_for_erc20(environment: "locust.env.Environment", **kwargs):
    if environment.parsed_options.exclude_tags and "erc20one" in environment.parsed_options.exclude_tags:
        return
    if environment.parsed_options.tags and "erc20one" not in environment.parsed_options.tags:
        return

    neon_client = NeonWeb3Client(environment.credentials["proxy_url"], environment.credentials["network_id"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    LOG.info("Deploy ERC20 contract for erc20one test")
    erc_contract, _ = neon_client.deploy_and_get_contract(ERC20_CONTRACT_NAME,
                                                          account=eth_account,
                                                          version=ERC20_CONTRACT_VERSION,
                                                          constructor_args=[web3.Web3.toWei(10000000000, "ether")])
    environment.erc20_one = {
        "user": eth_account,
        "contract": erc_contract
    }


@tag("erc20one")
class ERC20OneContractTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""
    def on_start(self) -> None:
        super().on_start()
        contract = self.user.environment.erc20_one["contract"]
        print(f"Main user {self.user.environment.erc20_one['user'].address} balance: "
              f"{contract.functions.balanceOf(self.user.environment.erc20_one['user'].address).call()}")
        self.web3_client.send_erc20(
            self.user.environment.erc20_one["user"],
            self.account, web3.Web3.toWei(1000, "ether"),
            contract.address,
            abi=contract.abi)


    @task
    def task_send_erc20(self):
        """Send ERC20 tokens"""
        print("Send erc20 ", self.account.address)
        contract = self.user.environment.erc20_one["contract"]
        recipient = random.choice(self.user.environment.shared.accounts)
        self.web3_client.send_erc20(
            self.account,
            recipient, 1,
            contract.address,
            abi=contract.abi)


class ERC20User(User):
    tasks = {
        ERC20TasksSet: 1,
        ERC20OneContractTasksSet: 5
    }