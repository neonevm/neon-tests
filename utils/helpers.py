import logging
import os
import pathlib
import random
import re
import string
import typing
import typing as tp
from queue import Queue

import allure
import base58
import polling2
import solcx
import web3
from eth_abi import abi, decode
from eth_abi.exceptions import InsufficientDataBytes
from eth_typing import HexStr
from eth_utils import keccak
from semantic_version import Version
from solana.rpc.commitment import Confirmed
from solcx import link_code
from solders.pubkey import Pubkey
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID, WRAPPED_SOL_MINT
from spl.token.instructions import get_associated_token_address
from web3 import Web3

from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest

T = tp.TypeVar("T")


@allure.step("Get contract abi")
def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[-1]:
            return compiled[key]
    return None


@allure.step("Get contract interface")
def get_contract_interface(
    contract: str,
    version: str,
    contract_name: tp.Optional[str] = None,
    import_remapping: tp.Optional[dict] = None,
    libraries: tp.Optional[dict] = None,
):
    if not contract.endswith(".sol"):
        contract += ".sol"
    if contract_name is None:
        if "/" in contract:
            contract_name = contract.rsplit("/", 1)[1].rsplit(".", 1)[0]
        else:
            contract_name = contract.rsplit(".", 1)[0]

    installed_version = solcx.install_solc(version)
    allure.attach(str(installed_version), "Installed solc version", allure.attachment_type.TEXT)
    if contract.startswith("/"):
        contract_path = pathlib.Path(contract)
    else:
        contract_path = (pathlib.Path.cwd() / "contracts" / f"{contract}").absolute()
        if not contract_path.exists():
            contract_path = (pathlib.Path.cwd() / "contracts" / "external" / f"{contract}").absolute()

    assert contract_path.exists(), f"Can't found contract: {contract_path}"

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=Version(version),
        import_remappings=import_remapping,
        allow_paths=["."],
        optimize=True,
    )  # this allow_paths isn't very good...
    contract_interface = get_contract_abi(contract_name, compiled)
    if libraries:
        contract_interface["bin"] = link_code(contract_interface["bin"], libraries, solc_version=Version(version))

    return contract_interface


@allure.step("Gen hash of block")
def gen_hash_of_block(size: int) -> str:
    """Generates a block hash of the given size"""
    try:
        block_hash = hex(int.from_bytes(os.urandom(size), "big"))
        if len(block_hash[2:]) == size * 2:
            return block_hash
        else:
            return gen_hash_of_block(size)
    except ValueError:
        return gen_hash_of_block(size)


@allure.step("Generate random text")
def generate_text(min_len: int = 2, max_len: int = 200, simple: bool = True) -> str:
    length = random.randint(min_len, max_len)
    if simple:
        chars = string.ascii_letters + string.digits
    else:
        chars = string.printable[:-5]
    return "".join(random.choice(chars) for _i in range(length)).strip()


@allure.step("Wait condition")
def wait_condition(
    func_cond: tp.Callable[..., T],
    timeout_sec: float = 15,
    delay: float = 0.5,
    args: tp.Tuple = (),
    kwargs: tp.Optional[dict[str, tp.Any]] = None,
    max_tries: tp.Optional[int] = None,
    check_success: tp.Callable[[T], bool] = polling2.is_truthy,
    step_function: tp.Callable[[float], float] = polling2.step_constant,
    ignore_exceptions: tp.Tuple[tp.Type[Exception], ...] = (KeyError,),
    poll_forever: bool = False,
    collect_values: tp.Optional[Queue] = None,
    log: int = logging.NOTSET,
    log_error: int = logging.NOTSET,
):
    return polling2.poll(
        target=func_cond,
        timeout=timeout_sec,
        step=delay,
        args=args,
        kwargs=kwargs,
        max_tries=max_tries,
        check_success=check_success,
        step_function=step_function,
        ignore_exceptions=ignore_exceptions,
        poll_forever=poll_forever,
        collect_values=collect_values,
        log=log,
        log_error=log_error,
    )


@allure.step("Decode function signature")
def decode_function_signature(function_name: str, args=None) -> HexStr:
    data = keccak(text=function_name)[:4]
    if args is not None:
        types = function_name.split("(")[1].split(")")[0].split(",")
        data += abi.encode(types, args)
    return HexStr("0x" + data.hex())


@allure.step("Decode function signature")
def decode_function_with_structure_in_arg_signature(function_name: str, args=None) -> str:
    data = keccak(text=function_name)[:4]
    if args is not None:
        match = re.search(r"\(\((.*?)\)\)", function_name)
        if match:
            inner = match.group(1)
            types = inner.split(",")
            data += abi.encode(types, args)
        else:
            print("No match found")
    return "0x" + data.hex()


@allure.step("Get functions signatures with params as keccak256 from contract abi")
def get_selectors(abi_):
    """Get functions signatures with params as keccak256 from contract abi"""
    selectors = []
    for function in filter(lambda item: item["type"] == "function", abi_):
        input_types = ""
        for input_ in function["inputs"]:
            if "struct" in input_["internalType"]:
                struct_name = input_["name"]
                struct_types = ",".join(i["type"] for i in input_["components"] if i["name"] != struct_name)
                input_types += "," + f"({struct_types})[]"
            else:
                input_types += "," + input_["type"]

        input_types = input_types[1:]
        encoded_selector = f"{function['name']}({input_types})"
        selectors.append(keccak(text=encoded_selector)[:4])
    return selectors


@allure.step("Create non-existing account address")
def create_invalid_address(length=20) -> str:
    """Create non-existing account address"""
    address = gen_hash_of_block(length)
    while web3.Web3.is_checksum_address(address):
        address = gen_hash_of_block(length)
    return address


def cryptohex(text: str):
    return "0x" + keccak(text=text).hex()


def int_to_hex(number: int):
    return int(number).to_bytes(32, "big").hex()


def hasattr_recursive(obj: typing.Any, attribute: str) -> bool:
    attr = attribute.split(".")
    temp_obj = obj
    for a in attr:
        if hasattr(temp_obj, a):
            temp_obj = getattr(temp_obj, a)
            continue
        return False

    return True


def bytes32_to_solana_pubkey(bytes32_data: str) -> Pubkey:
    byte_data = bytes.fromhex(bytes32_data)
    return Pubkey(byte_data)


def solana_pubkey_to_bytes32(solana_pubkey):
    byte_data = base58.b58decode(str(solana_pubkey))
    return byte_data


def pubkey2neon_address(pubkey: Pubkey) -> bytes:
    bytes_part = keccak(primitive=bytes(pubkey))[12:32]
    return bytes_part


def ether2bytes(ether: typing.Union[str, bytes]):
    if isinstance(ether, str):
        if ether.startswith("0x"):
            return bytes.fromhex(ether[2:])
        return bytes.fromhex(ether)
    return ether


def serialize_instruction(program_id: Pubkey, instruction) -> bytes:
    program_id_bytes = solana_pubkey_to_bytes32(program_id)
    serialized = program_id_bytes + len(instruction.accounts).to_bytes(8, "little")

    for key in instruction.accounts:
        serialized += bytes(key.pubkey)
        serialized += key.is_signer.to_bytes(1, "little")
        serialized += key.is_writable.to_bytes(1, "little")

    serialized += len(instruction.data).to_bytes(8, "little") + instruction.data
    return serialized


def serialize_instruction_struct(instruction) -> tuple[bytes, list[tuple[bytes, bool, bool]], bytes]:
    serialized_prog_id: bytes = solana_pubkey_to_bytes32(instruction.program_id)

    serialized_accounts = []
    for key in instruction.accounts:
        serialized_accounts.append((solana_pubkey_to_bytes32(key.pubkey), key.is_signer, key.is_writable))

    serialized_data = instruction.data
    return serialized_prog_id, serialized_accounts, serialized_data


def case_snake_to_camel(snake_str: str) -> str:
    components = snake_str.split("_")
    camel_case = components[0].lower() + "".join(x.title() for x in components[1:])
    return camel_case


def padhex(s, size):
    return "0x" + s[2:].zfill(size)


# Selector for revert and panic in Solidity.
SELECTOR_ERROR = Web3.keccak(text="Error(string)")[:4]
SELECTOR_PANIC = Web3.keccak(text="Panic(uint256)")[:4]

#  Panic-codes in Solidity
PANIC_CODES = {
    0x01: "Assertion violated or invalid enum value",
    0x11: "Arithmetic overflow or underflow",
    0x12: "Division or modulo by zero",
    0x21: "Shift by too large amount",
    0x22: "Access to invalid array index",
    0x31: "Pop from empty array",
    0x32: "Array too large or memory allocation overflow",
    0x41: "Too much memory allocated",
    0x51: "Callstack depth exceeded",
}


@allure.step("Decode error output of transaction")
def decode_error_output(data_hex):
    if not data_hex:
        return "Revert without reason"
    if not data_hex.startswith("0x"):
        data_hex = "0x" + data_hex

    data = Web3.to_bytes(hexstr=data_hex)
    # 1)  revert
    if len(data) == 0:
        return "Revert without reason"

    # 2) Error(string)
    if data[:4] == SELECTOR_ERROR:
        try:
            msg = decode(["string"], data[4:])
            return f"Error(string): {msg}"
        except Exception:
            return "Error(string) decoding failed"

    # 3) Panic(uint256)
    if data[:4] == SELECTOR_PANIC:
        try:
            code = decode(["uint256"], data[4:])[0]
        except InsufficientDataBytes:
            # If something wrong, return a raw hex
            return f"Panic(uint256): <cannot decode {data[4:].hex()}>"
        desc = PANIC_CODES.get(code, f"Unknown Panic code {code}")
        return f"Panic(uint256): {desc}"
    # 4) Unknow format
    return f"Unknown revert payload: {data_hex}"


def withdraw_neon_to_solana_eth_sign(web3_client, withdraw_from, withdraw_to, withdraw_contract):
    amount = web3_client.get_balance(withdraw_from)
    assert amount > 0, "Withdraw value should be > 0"
    data = decode_function_signature("withdraw_on_chain(bytes32)", [bytes(withdraw_to.pubkey())])
    """
        Withdraw contract requires trx value to be divisible to 10**9,
        remaining of the value are dropped with // operation.
    """
    tx_estimate = web3_client.make_raw_tx(
        from_=withdraw_from, to=withdraw_contract.address, amount=(amount // 10**9) * 10**9, data=data
    )
    value = (amount - web3_client.eth.estimate_gas(tx_estimate) * web3_client.gas_price()) // 10**9

    tx = web3_client.make_raw_tx(from_=withdraw_from, amount=value * 10**9)
    instruction_tx = withdraw_contract.functions.withdraw_on_chain(bytes(withdraw_to.pubkey())).build_transaction(tx)
    receipt = web3_client.send_transaction(withdraw_from, instruction_tx)
    assert receipt["status"] == 1


def withdraw_neon_to_solana_sol_sign(
    withdraw_from, withdraw_to, withdraw_contract, evm_loader, web3_client_sol, treasury_pool
):
    ata = get_associated_token_address(withdraw_to.pubkey(), WRAPPED_SOL_MINT)
    spl_token = SplToken(evm_loader, WRAPPED_SOL_MINT, TOKEN_PROGRAM_ID, withdraw_to)
    ata_balance_before = int(spl_token.get_balance(ata, commitment=Confirmed).value.amount)

    amount = web3_client_sol.get_balance(withdraw_from.checksum_address)
    assert amount > 0, "Withdraw value should be > 0"
    data = decode_function_signature("withdraw_on_chain(bytes32)", [bytes(withdraw_to.pubkey())])
    trx_estimate_obj = ScheduledTrxEstimateRequest(
        withdraw_from.checksum_address, withdraw_contract.address, data, amount
    )
    estimate_result = web3_client_sol.estimate_scheduled(withdraw_from.solana_account.pubkey(), [trx_estimate_obj])
    gas = web3_client_sol.gas_price() * int(estimate_result["gasList"][0], 16)
    """
        withdraw contract requires trx value to be divisible to 10**9
        remaining of the value are dropped with // operation
    """
    trx_estimate_obj.value = ((trx_estimate_obj.value - gas) // 10**9) * 10**9
    tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)
    evm_loader.create_tree_account(withdraw_from, treasury_pool, tx.encode())
    assert web3_client_sol.wait_for_transaction_receipt(tx.hash())["status"] == 1

    ata_balance_after = int(spl_token.get_balance(ata, commitment=Confirmed).value.amount)
    assert ata_balance_after >= ata_balance_before + trx_estimate_obj.value // 10**9

    balance_withdraw_from_after = web3_client_sol.get_balance(withdraw_from.checksum_address)
    assert balance_withdraw_from_after != amount


def parse_signature_types(signature: str) -> list[str]:
    # Remove function name and outer parentheses
    arg_str = signature[signature.find("(") + 1 : signature.rfind(")")]
    result = []
    current = []
    depth = 0

    i = 0
    while i < len(arg_str):
        char = arg_str[i]

        if char == "," and depth == 0:
            if current:
                result.append("".join(current).strip())
                current = []
        else:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            current.append(char)
        i += 1

    if current:
        result.append("".join(current).strip())

    return result
