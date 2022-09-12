import os
import pathlib

import solcx


def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[-1]:
            return compiled[key]


def get_contract_interface(contract: str, version: str, contract_name: str = None):
    if contract.endswith(".sol"):
        contract = contract.rsplit(".", 1)[0]

    if version not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(version)
    contract_path = (pathlib.Path.cwd() / "contracts" / f"{contract}.sol").absolute()

    assert contract_path.exists()

    compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version=version)
    contract_interface = get_contract_abi(contract_name or contract, compiled)

    return contract_interface


def gen_hash_of_block(size: int) -> str:
    """Generates a block hash of the given size"""
    try:
        block_hash = hex(int.from_bytes(os.urandom(size), "big"))
        if bytes.fromhex(block_hash[2:]):
            return block_hash
    except ValueError:
        return gen_hash_of_block(size)
