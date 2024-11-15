import json
import pathlib
import sys
import time
import typing as tp
from decimal import Decimal

import logging
import allure
import eth_account.signers.local
import requests
import web3
import web3.types
from eth_abi import abi
from eth_typing import BlockIdentifier
from web3.exceptions import TransactionNotFound

from utils.types import TransactionType
from utils import helpers
from utils.consts import InputTestConstants, Unit
from utils.helpers import decode_function_signature, case_snake_to_camel


LOG = logging.getLogger(__name__)


class Web3Client:
    def __init__(
        self,
        proxy_url: str,
        tracer_url: tp.Optional[tp.Any] = None,
        session: tp.Optional[tp.Any] = None,
    ):
        self._proxy_url = proxy_url
        self._tracer_url = tracer_url
        self._chain_id = None
        self._web3 = web3.Web3(web3.HTTPProvider(proxy_url, session=session, request_kwargs={"timeout": 30}))

    def __getattr__(self, item):
        return getattr(self._web3, item)

    @property
    @allure.step("Get native token name")
    def native_token_name(self):
        if self._proxy_url.split("/")[-1] != "solana":
            return self._proxy_url.split("/")[-1].upper()
        else:
            return "NEON"

    @property
    @allure.step("Get chain id")
    def chain_id(self):
        if self._chain_id is None:
            self._chain_id = self._web3.eth.chain_id
        return self._chain_id

    @allure.step("Get evm info")
    def _get_evm_info(self, method):
        resp = requests.post(
            self._proxy_url,
            json={"jsonrpc": "2.0", "method": method, "params": [], "id": 1},
        )
        resp.raise_for_status()
        try:
            body = resp.json()
            return body
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to decode EVM info: {resp.text}")

    @allure.step("Get proxy version")
    def get_proxy_version(self):
        return self._get_evm_info("neon_proxyVersion")

    @allure.step("Get cli version")
    def get_cli_version(self):
        return self._get_evm_info("neon_coreVersion")

    @allure.step("Get neon version")
    def get_neon_versions(self):
        return self._get_evm_info("neon_versions")

    @allure.step("Get evm version")
    def get_evm_version(self):
        return self._get_evm_info("web3_clientVersion")

    @allure.step("Get neon emulate")
    def get_neon_emulate(self, params):
        return requests.post(
            self._proxy_url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_emulate",
                "params": [params],
                "id": 0,
            },
        ).json()

    @allure.step("Get solana trx by neon")
    def get_solana_trx_by_neon(self, tr_id: str):
        return requests.post(
            self._proxy_url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_getSolanaTransactionByNeonTransaction",
                "params": [tr_id],
                "id": 0,
            },
        ).json()

    @allure.step("Get transaction by hash")
    def get_transaction_by_hash(self, transaction_hash):
        try:
            return self._web3.eth.get_transaction(transaction_hash)
        except TransactionNotFound:
            return None

    @allure.step("Get gas price")
    def gas_price(self):
        gas = self._web3.eth.gas_price
        return gas

    @allure.step("Get base fee per gas")
    def base_fee_per_gas(self) -> int:
        latest_block: web3.types.BlockData = self._web3.eth.get_block(block_identifier="latest")  # noqa
        base_fee = latest_block.baseFeePerGas  # noqa
        return base_fee

    @allure.step("Create account")
    def create_account(self) -> eth_account.signers.local.LocalAccount:
        return self._web3.eth.account.create()

    @allure.step("Get block number")
    def get_block_number(self):
        return self._web3.eth.get_block_number()

    @allure.step("Get block number by id")
    def get_block_number_by_id(self, block_identifier):
        return self._web3.eth.get_block(block_identifier)

    @allure.step("Get nonce")
    def get_nonce(
        self,
        address: tp.Union[eth_account.signers.local.LocalAccount, str],
        block: BlockIdentifier = "pending",
    ):
        address = address if isinstance(address, str) else address.address
        return self._web3.eth.get_transaction_count(address, block)

    @allure.step("Wait for transaction receipt")
    def wait_for_transaction_receipt(self, tx_hash, timeout=120):
        return self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    @allure.step("Get contract")
    def deploy_contract(
        self,
        from_: eth_account.signers.local.LocalAccount,
        abi,
        bytecode: str,
        gas: tp.Optional[int] = 0,
        gas_price: tp.Optional[int] = None,
        constructor_args: tp.Optional[tp.List] = None,
        value=0,
        tx_type: TransactionType = 0,
    ) -> web3.types.TxReceipt:
        """Proxy doesn't support send_transaction"""
        constructor_args = constructor_args or []

        contract = self._web3.eth.contract(abi=abi, bytecode=bytecode)
        tx_params = {
            "from": from_.address,
            "gas": gas,
            "nonce": self.get_nonce(from_),
            "value": value,
            "chainId": self.chain_id,
        }
        if tx_type is TransactionType.LEGACY:
            tx_params["gasPrice"] = gas_price or self.gas_price()

        transaction = contract.constructor(*constructor_args).build_transaction(tx_params)

        if transaction["gas"] == 0:
            transaction["gas"] = self._web3.eth.estimate_gas(transaction)

        signed_tx = self._web3.eth.account.sign_transaction(transaction, from_.key)
        tx = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self._web3.eth.wait_for_transaction_receipt(tx)

    @allure.step("Make raw tx")
    def make_raw_tx(
            self,
            from_: tp.Union[str, eth_account.signers.local.LocalAccount],
            to: tp.Optional[tp.Union[str, eth_account.signers.local.LocalAccount]] = None,
            amount: tp.Optional[tp.Union[int, float, Decimal]] = None,
            gas: tp.Optional[int] = None,
            gas_price: tp.Optional[int] = None,
            nonce: tp.Optional[int] = None,
            chain_id: tp.Optional[int] = None,
            data: tp.Optional[tp.Union[str, bytes]] = None,
            estimate_gas=False,
            tx_type: TransactionType = TransactionType.LEGACY,
    ) -> dict:
        if tx_type is TransactionType.LEGACY:
            if isinstance(from_, eth_account.signers.local.LocalAccount):
                transaction = {"from": from_.address}
            else:
                transaction = {"from": from_}

            if to:
                if isinstance(to, eth_account.signers.local.LocalAccount):
                    transaction["to"] = to.address
                if isinstance(to, str):
                    transaction["to"] = to
            if amount:
                transaction["value"] = amount
            if data:
                transaction["data"] = data
            if nonce is None:
                transaction["nonce"] = self.get_nonce(from_)
            else:
                transaction["nonce"] = nonce

            if chain_id is None:
                transaction["chainId"] = self.chain_id
            elif chain_id:
                transaction["chainId"] = chain_id

            if gas_price is None:
                gas_price = self.gas_price()
            transaction["gasPrice"] = gas_price
            if estimate_gas and not gas:
                gas = self._web3.eth.estimate_gas(transaction)
            if gas:
                transaction["gas"] = gas
        else:
            if gas_price is not None and gas is not None:
                max_priority_fee_per_gas, max_fee_per_gas = self.gas_price_to_eip1559_params(gas_price=gas_price)
            else:
                max_priority_fee_per_gas = max_fee_per_gas = "auto"

            transaction = self.make_raw_tx_eip_1559(
                chain_id="auto" if chain_id is None else chain_id,
                from_=from_,
                to=to,
                value=amount,
                nonce="auto" if nonce is None else nonce,
                data=data,
                access_list=None,
                gas="auto" if estimate_gas else gas,
                max_priority_fee_per_gas=max_priority_fee_per_gas,
                max_fee_per_gas=max_fee_per_gas,
            )
        return transaction

    @allure.step("Send transaction")
    def send_transaction(
        self,
        account: eth_account.signers.local.LocalAccount,
        transaction: tp.Dict,
        gas_multiplier: tp.Optional[float] = None,  # fix for some event depends transactions
        timeout: int = 120,
    ) -> web3.types.TxReceipt:
        instruction_tx = self._web3.eth.account.sign_transaction(transaction, account.key)
        signature = self._web3.eth.send_raw_transaction(instruction_tx.rawTransaction)
        return self._web3.eth.wait_for_transaction_receipt(signature, timeout=timeout)

    @allure.step("Create raw transaction EIP-1559")
    def make_raw_tx_eip_1559(
            self,
            *,
            chain_id: tp.Union[int, tp.Literal["auto"], None],
            from_: tp.Union[str, eth_account.signers.local.LocalAccount],
            to: tp.Optional[tp.Union[str, eth_account.signers.local.LocalAccount]],
            value: tp.Union[int, float, Decimal, str, None],
            nonce: tp.Union[int, tp.Literal["auto"], None],
            data: tp.Union[str, bytes, None],
            access_list: tp.Union[tp.List[web3.types.AccessListEntry], None],
            gas: tp.Union[int, tp.Literal["auto"], None],
            max_priority_fee_per_gas: tp.Union[int, tp.Literal["auto"], None],
            max_fee_per_gas: tp.Union[int, tp.Literal["auto"], None],
            base_fee_multiplier: float = 1.1,
    ) -> web3.types.TxParams:

        # Handle addresses
        if isinstance(from_, eth_account.signers.local.LocalAccount):
            from_ = from_.address

        if isinstance(to, eth_account.signers.local.LocalAccount):
            to = to.address

        # Create a copy of local variables and remove the redundant ones
        kwargs = locals().copy()
        del kwargs["self"]
        del kwargs["base_fee_multiplier"]

        # Move parameters related to gas to the end as they should be handled last
        for arg_name in ("gas", "max_priority_fee_per_gas", "max_fee_per_gas"):
            arg_value = kwargs[arg_name]
            del kwargs[arg_name]
            kwargs.update({arg_name: arg_value})

        # Initialize parameters with a default value "type": 2 for EIP-1559 transactions
        params = {"type": TransactionType.EIP_1559}

        # Map parameters with 'auto' value to their corresponding values
        base_fee_per_gas = 10

        if max_priority_fee_per_gas == "auto" or max_fee_per_gas == "auto":
            base_fee_per_gas = self.base_fee_per_gas()

        auto_map = {
            "chain_id": lambda: self.chain_id,
            "nonce": lambda: self.get_nonce(from_),
            "gas": lambda: self._web3.eth.estimate_gas(params),
            "max_priority_fee_per_gas": self._web3.eth._max_priority_fee,  # noqa
            "max_fee_per_gas": lambda: int((base_fee_per_gas * base_fee_multiplier) + params["maxPriorityFeePerGas"]),
        }

        # Iterate over parameters and add them to the params dictionary
        for param_name, param_value in kwargs.items():
            if param_value is None:
                continue

            if param_value == "auto":
                # get the auto value
                param_value = auto_map[param_name]()

            # Convert parameter name from snake_case to camelCase
            camel_case = case_snake_to_camel(param_name)

            # Add parameter to the params dictionary
            params[camel_case] = param_value

        # params keys validation happens here
        return web3.types.TxParams(params)

    @allure.step("Deploy and get contract")
    def deploy_and_get_contract(
        self,
        contract: str,
        version: str,
        account: eth_account.signers.local.LocalAccount,
        contract_name: tp.Optional[str] = None,
        constructor_args: tp.Optional[tp.Any] = None,
        import_remapping: tp.Optional[dict] = None,
        libraries: tp.Optional[dict] = None,
        gas: tp.Optional[int] = 0,
        value=0,
        tx_type: TransactionType = TransactionType.LEGACY,
    ) -> tp.Tuple[tp.Any, web3.types.TxReceipt]:
        contract_interface = helpers.get_contract_interface(
            contract,
            version,
            contract_name=contract_name,
            import_remapping=import_remapping,
            libraries=libraries,
        )

        contract_deploy_tx = self.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=constructor_args,
            gas=gas,
            value=value,
            tx_type=tx_type,
        )

        contract = self.eth.contract(address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"])

        return contract, contract_deploy_tx

    @allure.step("Compile by vyper and deploy")
    def compile_by_vyper_and_deploy(self, account, contract_name, constructor_args=None):
        import vyper  # Import here because vyper prevent override decimal precision (uses in economy tests)

        contract_path = pathlib.Path.cwd() / "contracts" / "vyper"
        with open(contract_path / f"{contract_name}.vy") as f:
            contract_code = f.read()
            contract_interface = vyper.compile_code(contract_code, output_formats=["abi", "bytecode"])

        contract_deploy_tx = self.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bytecode"],
            constructor_args=constructor_args,
        )
        return self.eth.contract(address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"])

    @staticmethod
    @allure.step("Text to bytes32")
    def text_to_bytes32(text: str) -> bytes:
        return text.encode().ljust(32, b"\0")

    @allure.step("Call function at address")
    def call_function_at_address(self, contract_address, signature, args, result_types):
        calldata = decode_function_signature(signature, args)
        tx = {
            "data": calldata,
            "to": contract_address,
        }
        result = self._web3.eth.call(tx)
        return abi.decode(result_types, result)[0]

    @allure.step("Get balance")
    def get_balance(
        self,
        address: tp.Union[str, eth_account.signers.local.LocalAccount],
        unit=Unit.WEI,
    ):
        if not isinstance(address, str):
            address = address.address
        balance = self._web3.eth.get_balance(address, "pending")
        if unit != Unit.WEI:
            balance = self._web3.from_wei(balance, unit.value)
        return balance

    @allure.step("Get deployed contract")
    def get_deployed_contract(
        self,
        address,
        contract_file,
        contract_name=None,
        solc_version="0.8.12",
        import_remapping: tp.Optional[dict] = None,
    ):
        contract_interface = helpers.get_contract_interface(
            contract_file, solc_version, contract_name, import_remapping=import_remapping
        )
        contract = self.eth.contract(address=address, abi=contract_interface["abi"])
        return contract

    @allure.step("Send tokens")
    def send_tokens(
        self,
        from_: eth_account.signers.local.LocalAccount,
        to: tp.Union[str, eth_account.signers.local.LocalAccount],
        value: int,
        gas: tp.Optional[int] = None,
        gas_price: tp.Optional[int] = None,
        nonce: int = None,
        tx_type: TransactionType = TransactionType.LEGACY,
    ) -> web3.types.TxReceipt:
        if tx_type is TransactionType.LEGACY:
            transaction = self.make_raw_tx(
                from_, to, amount=value, gas=gas, gas_price=gas_price, nonce=nonce, estimate_gas=True
            )
        else:
            if gas_price is not None:
                max_priority_fee_per_gas, max_fee_per_gas = self.gas_price_to_eip1559_params(gas_price=gas_price)
            else:
                max_priority_fee_per_gas = max_fee_per_gas = "auto"

            transaction = self.make_raw_tx_eip_1559(
                chain_id="auto",
                from_=from_,
                to=to,
                value=value,
                nonce="auto" if nonce is None else nonce,
                data=None,
                access_list=None,
                gas="auto" if gas is None else gas,
                max_priority_fee_per_gas=max_priority_fee_per_gas,
                max_fee_per_gas=max_fee_per_gas,
            )
        signed_tx = self.eth.account.sign_transaction(transaction, from_.key)
        tx = self.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.eth.wait_for_transaction_receipt(tx)

    @allure.step("Send tokens under EIP-1559")
    def send_tokens_eip_1559(
            self,
            *,
            from_: eth_account.signers.local.LocalAccount,
            to: tp.Union[str, eth_account.signers.local.LocalAccount],
            value: tp.Union[int, float, Decimal, str, None],
            chain_id: tp.Union[int, tp.Literal["auto"], None] = "auto",
            nonce: tp.Union[int, tp.Literal["auto"], None] = "auto",
            gas: tp.Union[int, tp.Literal["auto"], None] = "auto",
            max_priority_fee_per_gas: tp.Union[int, tp.Literal["auto"], None] = "auto",
            max_fee_per_gas: tp.Union[int, tp.Literal["auto"], None] = "auto",
            base_fee_multiplier: float = 1.1,
            access_list: tp.Optional[tp.List[web3.types.AccessListEntry]] = None,
            timeout: int = 120,
    ) -> web3.types.TxReceipt:

        tx_params = self.make_raw_tx_eip_1559(
            chain_id=chain_id,
            from_=from_.address,
            to=to,
            value=value,
            nonce=nonce,
            gas=gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            max_fee_per_gas=max_fee_per_gas,
            data=None,
            access_list=access_list,
            base_fee_multiplier=base_fee_multiplier,
        )

        receipt = self.send_transaction(account=from_, transaction=tx_params, timeout=timeout)
        return receipt

    @allure.step("Send all neons from one account to another")
    def send_all_neons(
        self,
        from_: eth_account.signers.local.LocalAccount,
        to: tp.Union[str, eth_account.signers.local.LocalAccount],
        gas: tp.Optional[int] = None,
        gas_price: tp.Optional[int] = None,
        nonce: int = None,
    ) -> web3.types.TxReceipt:
        value = self.get_balance(from_.address)
        transaction = self.make_raw_tx(
            from_, to, amount=value, gas=gas, gas_price=gas_price, nonce=nonce, estimate_gas=True
        )
        transaction["value"] = float(value) - float(transaction["gas"] * transaction["gasPrice"] * 1.1)

        if transaction["value"] > 0:
            transaction["value"] = web3.Web3.to_wei(transaction["value"], Unit.WEI)
            signed_tx = self.eth.account.sign_transaction(transaction, from_.key)
            tx = self.eth.send_raw_transaction(signed_tx.rawTransaction)
            self.eth.wait_for_transaction_receipt(tx)
        else:
            LOG.info(f"Not enough funds to send all neons from {from_.address} account")

    @staticmethod
    @allure.step("To atomic currency")
    def to_atomic_currency(amount):
        return web3.Web3.to_wei(amount, "ether")

    @allure.step("To main currency")
    def to_main_currency(self, value):
        return web3.Web3.from_wei(value, "ether")

    @allure.step("Calculate trx gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> int:
        tx = self._web3.eth.get_transaction(tx_receipt.transactionHash)
        gas_used_in_tx = tx_receipt.gasUsed * tx["gasPrice"]
        return gas_used_in_tx

    def get_token_usd_gas_price(self):
        resp = requests.post(
            self._proxy_url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_gasPrice",
                "params": [],
                "id": 0,
            },
        ).json()
        return int(resp["result"]["tokenPriceUsd"], 16) / 100000

    def gas_price_to_eip1559_params(self, gas_price: int) -> tuple[int, int]:
        base_fee_per_gas = self.base_fee_per_gas()

        msg = f"gas_price {gas_price} is lower than the baseFeePerGas {base_fee_per_gas}"
        assert gas_price >= base_fee_per_gas, msg

        max_fee_per_gas = gas_price
        max_priority_fee_per_gas = max_fee_per_gas - base_fee_per_gas
        return max_priority_fee_per_gas, max_fee_per_gas

    def is_trx_iterative(self, trx_hash: str) -> bool:
        resp = requests.post(
            self._proxy_url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_getSolanaTransactionByNeonTransaction",
                "params": [trx_hash],
                "id": 0,
            },
        ).json()
        return len(resp["result"]) > 1


class NeonChainWeb3Client(Web3Client):
    def __init__(
        self,
        proxy_url: str,
        tracer_url: tp.Optional[tp.Any] = None,
        session: tp.Optional[tp.Any] = None,
    ):
        super().__init__(proxy_url, tracer_url, session)

    @allure.step("Create account with balance")
    def create_account_with_balance(
        self,
        faucet,
        amount: int = InputTestConstants.NEW_USER_REQUEST_AMOUNT.value,
        bank_account=None,
    ) -> eth_account.signers.local.LocalAccount:
        """Creates a new account with balance"""
        account = self.create_account()
        if bank_account is not None:
            self.send_neon(bank_account, account, amount)
        else:
            faucet.request_neon(account.address, amount=amount)
        return account

    @allure.step("Send neon")
    def send_neon(
        self,
        from_: eth_account.signers.local.LocalAccount,
        to: tp.Union[str, eth_account.signers.local.LocalAccount],
        amount: tp.Union[int, float, Decimal],
        gas: tp.Optional[int] = None,
        gas_price: tp.Optional[int] = None,
        nonce: int = None,
    ) -> web3.types.TxReceipt:
        value = web3.Web3.to_wei(amount, "ether")
        return self.send_tokens(from_, to, value, gas, gas_price, nonce)
