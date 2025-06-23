import pathlib
import typing as tp

import allure
import eth_abi
from eth_utils import abi

from Crypto.Hash import keccak
from eth_account.datastructures import SignedTransaction
from solders.pubkey import Pubkey
from web3.auto import w3

from utils.logger import log_text_to_allure_and_stdout
from utils.types import Caller, Contract
from .contract import get_contract_bin
from .eth_tx_utils import pack


@allure.step("Create contract address")
def create_contract_address(
    user: tp.Union[Caller, bytes],
    evm_loader,
    chain_id: int | str | None = "",
) -> Contract:
    if chain_id == "":
        chain_id = evm_loader.chain_id

    # Create contract address from (caller_address, nonce)
    if isinstance(user, Caller):
        user = user.eth_address
    user_nonce = evm_loader.get_neon_nonce(user, chain_id)
    contract_eth_address = keccak.new(digest_bits=256).update(pack([user, user_nonce or None])).digest()[-20:]

    contract_solana_address, _ = evm_loader.ether2program(contract_eth_address)
    contract_neon_address = evm_loader.ether2balance(contract_eth_address, chain_id)

    contract = Contract(contract_eth_address, Pubkey.from_string(contract_solana_address), contract_neon_address)
    log_text_to_allure_and_stdout("Created contract addresses", str(contract))

    return contract


@allure.step("Prepare signed transaction for contract deployment")
def make_deployment_transaction(
    evm_loader,
    user: Caller,
    contract_file_name: tp.Union[pathlib.Path, str],
    contract_name: tp.Optional[str] = None,
    encoded_args=None,
    value: int = 0,
    gas: int = 999999999,
    chain_id: int | str | None = "",
    access_list=None,
    max_priority_fee_per_gas=None,
    max_fee_per_gas=None,
    version: str = "0.7.6",
    import_remappings: dict | list = None,
) -> SignedTransaction:
    if chain_id == "":
        chain_id = evm_loader.chain_id
    data = get_contract_bin(contract_file_name, contract_name, version, import_remappings)
    if encoded_args is not None:
        data = data + encoded_args.hex()

    nonce = evm_loader.get_neon_nonce(user.eth_address, chain_id)

    tx = {"to": None, "value": 0, "gas": gas, "gasPrice": 0, "nonce": nonce, "data": data}
    if chain_id:
        tx["chainId"] = chain_id

    if access_list:
        tx["accessList"] = access_list
        tx["type"] = 1
    if value:
        tx["value"] = value
    if max_priority_fee_per_gas:
        tx["maxPriorityFeePerGas"] = max_priority_fee_per_gas
    if max_fee_per_gas:
        tx["maxFeePerGas"] = max_fee_per_gas
        tx.pop("gasPrice")

    return w3.eth.account.sign_transaction(tx, user.solana_account.secret()[:32])


@allure.step("Prepare signed transaction")
def make_eth_transaction(
    evm_loader,
    to_addr: bytes,
    data: tp.Union[bytes, None],
    caller: Caller,
    value: int = 0,
    chain_id: int | str | None = "",
    gas=9999999999,
    max_priority_fee_per_gas=None,
    max_fee_per_gas=None,
    access_list=None,
    type_=None,
    gas_price=0,
) -> SignedTransaction:
    if chain_id == "":
        chain_id = evm_loader.chain_id

    nonce = evm_loader.get_neon_nonce(caller.eth_address)
    tx = {"to": to_addr, "value": value, "gas": gas, "gasPrice": gas_price, "nonce": nonce}

    if chain_id is not None:
        tx["chainId"] = chain_id

    if data is not None:
        tx["data"] = data

    if access_list is not None:
        tx["accessList"] = access_list

    if max_priority_fee_per_gas is not None:
        tx["maxPriorityFeePerGas"] = max_priority_fee_per_gas

    if max_fee_per_gas is not None:
        tx["maxFeePerGas"] = max_fee_per_gas
        tx.pop("gasPrice")

    if type_ is not None:
        tx["type"] = type_
    log_text_to_allure_and_stdout("Ethereum transaction data", str(tx))
    return w3.eth.account.sign_transaction(tx, caller.solana_account.secret()[:32])


@allure.step("Prepare signed transaction for contract call")
def make_contract_call_trx(
    evm_loader,
    user,
    contract,
    function_signature: str,
    params: tp.Iterable[tp.Any] | None = None,
    value=0,
    chain_id: int | str | None = "",
    access_list=None,
    gas=999999999,
    gas_price=0,
    max_priority_fee_per_gas=None,
    max_fee_per_gas=None,
    trx_type=None,
) -> SignedTransaction:
    if chain_id == "":
        chain_id = evm_loader.chain_id

    # does not work for tuple in params
    data = abi.function_signature_to_4byte_selector(function_signature)

    if params is not None:
        types = function_signature.split("(")[1].split(")")[0].split(",")
        data += eth_abi.encode(types, params)

    if isinstance(contract, Contract):
        contract_addr = contract.eth_address
    else:
        contract_addr = contract
    signed_tx = make_eth_transaction(
        evm_loader,
        contract_addr,
        data,
        user,
        value=value,
        chain_id=chain_id,
        gas=gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        max_fee_per_gas=max_fee_per_gas,
        access_list=access_list,
        type_=trx_type,
        gas_price=gas_price,
    )

    return signed_tx
