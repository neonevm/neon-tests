import typing as tp
import pathlib

import solcx
from semantic_version import Version


def get_contract_bin(
    contract: str,
    contract_name: tp.Optional[str] = None,
    version: str = "0.7.6",
):
    if not contract.endswith(".sol"):
        contract += ".sol"
    if contract_name is None:
        if "/" in contract:
            contract_name = contract.rsplit("/", 1)[1].rsplit(".", 1)[0]
        else:
            contract_name = contract.rsplit(".", 1)[0]

    solcx.install_solc(version)

    contract_path = (pathlib.Path.cwd() / "contracts" / "neon_evm" / contract).absolute()
    if not contract_path.exists():
        contract_path = (pathlib.Path.cwd() / "contracts" / f"{contract}").absolute()

    assert contract_path.exists(), f"Can't found contract: {contract_path}"

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=Version(version),
        allow_paths=["."],
        optimize=True,
    )
    contract_abi = None
    for key in compiled.keys():
        if contract_name == key.rsplit(":")[-1]:
            contract_abi = compiled[key]
            break

    return contract_abi["bin"]
