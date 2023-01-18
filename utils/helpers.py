import os
import asyncio
import pathlib
import random
import string
import time
import typing as tp

import solcx
from pythclient.pythaccounts import PythPriceAccount
from pythclient.solana import SolanaClient, SolanaPublicKey, SOLANA_MAINNET_HTTP_ENDPOINT


def get_sol_price() -> float:
    """Get SOL price from Solana mainnet"""

    async def get_price():
        account_key = SolanaPublicKey("H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG")
        solana_client = SolanaClient(endpoint=SOLANA_MAINNET_HTTP_ENDPOINT)
        price: PythPriceAccount = PythPriceAccount(account_key, solana_client)
        await price.update()
        await solana_client.close()
        return price.aggregate_price

    result = asyncio.run(get_price())
    return result


def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[-1]:
            return compiled[key]


def get_contract_interface(contract: str, version: str, contract_name: tp.Optional[str] = None,
                           import_remapping: tp.Optional[dict] = None):
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

    assert contract_path.exists(), f"Can't found contract: {contract_path}"

    compiled = solcx.compile_files([contract_path],
                                   output_values=["abi", "bin"],
                                   solc_version=version,
                                   import_remappings=import_remapping,
                                   allow_paths=["."],
                                   optimize=True
                                   )  # this allow_paths isn't very good...
    contract_interface = get_contract_abi(contract_name, compiled)

    return contract_interface


def gen_hash_of_block(size: int) -> str:
    """Generates a block hash of the given size"""
    try:
        block_hash = hex(int.from_bytes(os.urandom(size), "big"))
        print(len(block_hash))
        if bytes.fromhex(block_hash[2:]) or len(block_hash[2:]) != size * 2:
            return block_hash
    except ValueError:
        return gen_hash_of_block(size)


def generate_text(min_len: int = 2, max_len: int = 200, simple: bool = True) -> str:
    length = random.randint(min_len, max_len)
    if simple:
        chars = string.ascii_letters + string.digits
    else:
        chars = string.printable[:-5]
    return ''.join(random.choice(chars) for _i in range(length)).strip()


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
