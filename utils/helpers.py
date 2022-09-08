import os
import pathlib
import typing as tp

import solcx


def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[1]:
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
        if bytes.fromhex(block_hash[2:]):
            return block_hash
    except ValueError:
        return gen_hash_of_block(size)
