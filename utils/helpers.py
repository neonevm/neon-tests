import os
import pathlib
import random
import string
import time
import typing as tp

import web3
import solcx
from eth_abi import abi
from eth_utils import keccak


def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[-1]:
            return compiled[key]


def get_contract_interface(
    contract: str,
    version: str,
    contract_name: tp.Optional[str] = None,
    import_remapping: tp.Optional[dict] = None,
):
    if not contract.endswith(".sol"):
        contract += ".sol"
    if contract_name is None:
        if "/" in contract:
            contract_name = contract.rsplit("/", 1)[1].rsplit(".", 1)[0]
        else:
            contract_name = contract.rsplit(".", 1)[0]

    if version not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(version)
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
        solc_version=version,
        import_remappings=import_remapping,
        allow_paths=["."],
        optimize=True,
    )  # this allow_paths isn't very good...
    contract_interface = get_contract_abi(contract_name, compiled)

    return contract_interface


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


def generate_text(min_len: int = 2, max_len: int = 200, simple: bool = True) -> str:
    length = random.randint(min_len, max_len)
    if simple:
        chars = string.ascii_letters + string.digits
    else:
        chars = string.printable[:-5]
    return "".join(random.choice(chars) for _i in range(length)).strip()


def wait_condition(func_cond, timeout_sec=15, delay=0.5):
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout_sec:
            raise TimeoutError(f"The condition not reached within {timeout_sec} sec")
        try:
            if func_cond():
                break

        except Exception as e:
            print(f"Error during waiting: {e}")
        time.sleep(delay)
    return True


def decode_function_signature(function_name: str, args=None) -> str:
    data = keccak(text=function_name)[:4]
    if args is not None:
        types = function_name.split("(")[1].split(")")[0].split(",")
        data += abi.encode(types, args)
    return "0x" + data.hex()


def get_selectors(abi):
    """Get functions signatures with params as keccak256 from contract abi"""
    selectors = []
    for function in filter(lambda item: item["type"] == "function", abi):
        input_types = ""
        for input in function["inputs"]:
            if "struct" in input["internalType"]:
                struct_name = input["name"]
                struct_types = ",".join(i["type"] for i in input["components"] if i["name"] != struct_name)
                input_types += "," + f"({struct_types})[]"
            else:
                input_types += "," + input["type"]

        input_types = input_types[1:]
        encoded_selector = f"{function['name']}({input_types})"
        selectors.append(keccak(text=encoded_selector)[:4])
    return selectors


def create_invalid_address(length=20) -> str:
    """Create non-existing account address"""
    address = gen_hash_of_block(length)
    while web3.Web3.is_checksum_address(address):
        address = gen_hash_of_block(length)
    return address
