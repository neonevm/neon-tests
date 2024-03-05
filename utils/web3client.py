import json
import pathlib
import time
import typing as tp
from decimal import Decimal

import allure
import eth_account.signers.local
import requests
import web3
import web3.types
from eth_abi import abi
from web3.exceptions import TransactionNotFound

from utils import helpers
from utils.consts import InputTestConstants, Unit
from utils.helpers import decode_function_signature


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
        return self._get_evm_info("neon_proxy_version")

    @allure.step("Get cli version")
    def get_cli_version(self):
        return self._get_evm_info("neon_cli_version")
    
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

    @allure.step("Create account")
    def create_account(self):
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
        block: str = "pending",
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
    ) -> web3.types.TxReceipt:
        """Proxy doesn't support send_transaction"""
        gas_price = gas_price or self.gas_price()
        constructor_args = constructor_args or []

        contract = self._web3.eth.contract(abi=abi, bytecode=bytecode)
        transaction = contract.constructor(*constructor_args).build_transaction(
            {
                "from": from_.address,
                "gas": gas,
                "gasPrice": gas_price,
                "nonce": self.get_nonce(from_),
                "value": value,
                "chainId": self.chain_id,
            }
        )

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
    ) -> dict:
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
    ) -> web3.types.TxReceipt:
        transaction = self.make_raw_tx(
            from_, to, amount=value, gas=gas, gas_price=gas_price, nonce=nonce, estimate_gas=True
        )

        signed_tx = self.eth.account.sign_transaction(transaction, from_.key)
        tx = self.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.eth.wait_for_transaction_receipt(tx)

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
    ):
        """Creates a new account with balance"""
        account = self.create_account()
        balance_before = float(self.from_wei(self.eth.get_balance(account.address), Unit.ETHER))

        if bank_account is not None:
            self.send_neon(bank_account, account, amount)
        else:
            faucet.request_neon(account.address, amount=amount)
        for _ in range(20):
            if float(self.from_wei(self.eth.get_balance(account.address), Unit.ETHER)) >= (balance_before + amount):
                break
            time.sleep(1)
        else:
            raise AssertionError(f"Balance didn't changed after 20 seconds ({account.address})")
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
