import typing as tp
import pathlib

import eth_abi
import solcx
from eth_account.datastructures import SignedTransaction
from eth_utils import abi
from solana.keypair import Keypair
from solana.publickey import PublicKey

from utils.evm_loader import EvmLoader
from utils.types import Caller, TreasuryPool, Contract
from .constants import NEON_CORE_API_URL
from .neon_api_client import NeonApiClient
from .transaction_checks import check_transaction_logs_have_text

from .storage import create_holder
from .ethereum import create_contract_address, make_eth_transaction
from semantic_version import Version

from web3.auto import w3


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


def make_deployment_transaction(
    evm_loader: EvmLoader,
    user: Caller,
    contract_file_name: tp.Union[pathlib.Path, str],
    contract_name: tp.Optional[str] = None,
    encoded_args=None,
    value: int = 0,
    gas: int = 999999999,
    chain_id=111,
    access_list=None,
    max_priority_fee_per_gas=None,
    max_fee_per_gas=None,
    version: str = "0.7.6",
) -> SignedTransaction:
    data = get_contract_bin(contract_file_name, contract_name, version)
    if encoded_args is not None:
        data = data + encoded_args.hex()

    nonce = evm_loader.get_neon_nonce(user.eth_address)
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

    return w3.eth.account.sign_transaction(tx, user.solana_account.secret_key[:32])


def make_contract_call_trx(
    evm_loader,
    user,
    contract,
    function_signature,
    params=None,
    value=0,
    chain_id=111,
    access_list=None,
    max_priority_fee_per_gas=None,
    max_fee_per_gas=None,
    trx_type=None,
):
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
        access_list=access_list,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        max_fee_per_gas=max_fee_per_gas,
        type=trx_type,
    )

    return signed_tx


def deploy_contract(
    operator: Keypair,
    user: Caller,
    contract_file_name: tp.Union[pathlib.Path, str],
    evm_loader: EvmLoader,
    treasury_pool: TreasuryPool,
    value: int = 0,
    encoded_args=None,
    contract_name: tp.Optional[str] = None,
    version: str = "0.7.6",
):
    neon_api_client = NeonApiClient(url=NEON_CORE_API_URL)

    contract_code = get_contract_bin(contract_file_name, contract_name=contract_name, version=version)
    if encoded_args is None:
        encoded_args = b""
    emulate_result = neon_api_client.emulate(
        user.eth_address.hex(), contract=None, data=contract_code + encoded_args.hex()
    )
    additional_accounts = [PublicKey(item["pubkey"]) for item in emulate_result["solana_accounts"]]

    contract: Contract = create_contract_address(user, evm_loader)
    holder_acc = create_holder(operator, evm_loader)
    signed_tx = make_deployment_transaction(
        evm_loader, user, contract_file_name, contract_name, encoded_args=encoded_args, value=value, version=version
    )
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator)

    resp = evm_loader.execute_transaction_steps_from_account(operator, treasury_pool, holder_acc, additional_accounts)
    check_transaction_logs_have_text(resp, "exit_status=0x12")
    return contract
