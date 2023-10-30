import json
import pathlib
import time
import typing as tp
from decimal import Decimal

import web3
import web3.types
import requests
import eth_account.signers.local
from eth_abi import abi
from web3.exceptions import TransactionNotFound

from utils import helpers
from utils.consts import InputTestConstants, Unit
from utils.helpers import decode_function_signature


class NeonWeb3Client:
    def __init__(
        self,
        proxy_url: str,
        chain_id: int,
        tracer_url: tp.Optional[tp.Any] = None,
        session: tp.Optional[tp.Any] = None,
    ):
        self._proxy_url = proxy_url
        self._tracer_url = tracer_url
        self._web3 = web3.Web3(
            web3.HTTPProvider(
                proxy_url, session=session, request_kwargs={"timeout": 30}
            )
        )
        self._chain_id = chain_id
        self._session = session

    def __getattr__(self, item):
        return getattr(self._web3, item)

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

    def get_proxy_version(self):
        return self._get_evm_info("neon_proxy_version")

    def get_cli_version(self):
        return self._get_evm_info("neon_cli_version")

    def get_evm_version(self):
        return self._get_evm_info("web3_clientVersion")

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

    def get_transaction_by_hash(self, transaction_hash):
        try:
            return self._web3.eth.get_transaction(transaction_hash)
        except TransactionNotFound:
            return None

    def gas_price(self):
        gas = self._web3.eth.gas_price
        return gas

    def create_account(self):
        return self._web3.eth.account.create()

    def create_account_with_balance(
        self,
        faucet,
        amount: int = InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value,
        bank_account=None,
    ):
        """Creates a new account with balance"""
        account = self.create_account()
        balance_before = float(
            self.from_wei(self.eth.get_balance(account.address), Unit.ETHER)
        )

        if bank_account is not None:
            self.send_neon(bank_account, account, amount)
        else:
            faucet.request_neon(account.address, amount=amount)
        for _ in range(20):
            if float(
                self.from_wei(self.eth.get_balance(account.address), Unit.ETHER)
            ) >= (balance_before + amount):
                break
            time.sleep(1)
        else:
            raise AssertionError(
                f"Balance didn't changed after 20 seconds ({account.address})"
            )
        return account

    def get_balance(
        self, address: tp.Union[str, eth_account.signers.local.LocalAccount]
    ):
        if not isinstance(address, str):
            address = address.address
        return web3.Web3.from_wei(
            self._web3.eth.get_balance(address, "pending"), "ether"
        )

    def get_block_number(self):
        return self._web3.eth.get_block_number()

    def get_block_number_by_id(self, block_identifier):
        return self._web3.eth.get_block(block_identifier)

    def get_nonce(
        self,
        address: tp.Union[eth_account.signers.local.LocalAccount, str],
        block: str = "pending",
    ):
        address = address if isinstance(address, str) else address.address
        return self._web3.eth.get_transaction_count(address, block)

    def send_neon(
        self,
        from_: eth_account.signers.local.LocalAccount,
        to: tp.Union[str, eth_account.signers.local.LocalAccount],
        amount: tp.Union[int, float, Decimal],
        gas: tp.Optional[int] = 0,
        gas_price: tp.Optional[int] = None,
        nonce: int = None,
    ) -> web3.types.TxReceipt:
        to_addr = to if isinstance(to, str) else to.address
        if nonce is None:
            nonce = self.get_nonce(from_)
        transaction = {
            "from": from_.address,
            "to": to_addr,
            "value": web3.Web3.to_wei(amount, "ether"),
            "chainId": self._chain_id,
            "gasPrice": gas_price or self.gas_price(),
            "gas": gas,
            "nonce": nonce,
        }
        if transaction["gas"] == 0:
            transaction["gas"] = self._web3.eth.estimate_gas(transaction)

        signed_tx = self._web3.eth.account.sign_transaction(transaction, from_.key)
        tx = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self._web3.eth.wait_for_transaction_receipt(tx)

    def deploy_contract(
        self,
        from_: eth_account.signers.local.LocalAccount,
        abi,
        bytecode: str,
        gas: tp.Optional[int] = 0,
        gas_price: tp.Optional[int] = None,
        constructor_args: tp.Optional[tp.List] = None,
    ) -> web3.types.TxReceipt:
        """Proxy doesn't support send_transaction"""
        gas_price = gas_price or self.gas_price()
        constructor_args = constructor_args or []

        contract = self._web3.eth.contract(abi=abi, bytecode=bytecode)
        transaction = contract.constructor(*constructor_args).build_transaction(
            {
                "chainId": self._chain_id,
                "from": from_.address,
                "gas": gas,
                "gasPrice": gas_price,
                "nonce": self.get_nonce(from_),
            }
        )

        if transaction["gas"] == 0:
            transaction["gas"] = self._web3.eth.estimate_gas(transaction)

        signed_tx = self._web3.eth.account.sign_transaction(transaction, from_.key)
        tx = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self._web3.eth.wait_for_transaction_receipt(tx)

    def send_transaction(
        self,
        account: eth_account.signers.local.LocalAccount,
        transaction: tp.Dict,
        gas_multiplier: tp.Optional[
            float
        ] = None,  # fix for some event depends transactions
    ) -> web3.types.TxReceipt:
        if "gasPrice" not in transaction:
            transaction["gasPrice"] = self.gas_price()
        if "gas" not in transaction:
            transaction["gas"] = self._web3.eth.estimate_gas(transaction)
        if gas_multiplier is not None:
            transaction["gas"] = int(transaction["gas"] * gas_multiplier)
        instruction_tx = self._web3.eth.account.sign_transaction(
            transaction, account.key
        )
        signature = self._web3.eth.send_raw_transaction(instruction_tx.rawTransaction)
        return self._web3.eth.wait_for_transaction_receipt(signature)

    def deploy_and_get_contract(
        self,
        contract: str,
        version: str,
        account: eth_account.signers.local.LocalAccount,
        contract_name: tp.Optional[str] = None,
        constructor_args: tp.Optional[tp.Any] = None,
        import_remapping: tp.Optional[dict] = None,
        gas: tp.Optional[int] = 0,
    ) -> tp.Tuple[tp.Any, web3.types.TxReceipt]:
        contract_interface = helpers.get_contract_interface(
            contract,
            version,
            contract_name=contract_name,
            import_remapping=import_remapping,
        )

        contract_deploy_tx = self.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=constructor_args,
            gas=gas,
        )

        contract = self.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

        return contract, contract_deploy_tx

    def compile_by_vyper_and_deploy(
        self, account, contract_name, constructor_args=None
    ):
        import vyper  # Import here because vyper prevent override decimal precision (uses in economy tests)

        contract_path = pathlib.Path.cwd() / "contracts" / "vyper"
        with open(contract_path / f"{contract_name}.vy") as f:
            contract_code = f.read()
            contract_interface = vyper.compile_code(
                contract_code, output_formats=["abi", "bytecode"]
            )

        contract_deploy_tx = self.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bytecode"],
            constructor_args=constructor_args,
        )
        return self.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

    @staticmethod
    def text_to_bytes32(text: str) -> bytes:
        return text.encode().ljust(32, b"\0")

    def call_function_at_address(self, contract_address, signature, args, result_types):
        calldata = decode_function_signature(signature, args)
        tx = {
            "data": calldata,
            "to": contract_address,
        }
        result = self._web3.eth.call(tx)
        return abi.decode(result_types, result)[0]
