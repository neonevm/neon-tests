import typing as tp
import pathlib

import eth_abi
import solcx
from eth_account.datastructures import SignedTransaction
from eth_utils import abi
from solana.keypair import Keypair

from ..types.types import Caller, Contract, TreasuryPool
from ..solana_utils import EvmLoader, write_transaction_to_holder_account, send_transaction_step_from_account
from .storage import create_holder
from .ethereum import create_contract_address, make_eth_transaction

from web3.auto import w3


def get_contract_bin(
    contract: str,
    contract_name: tp.Optional[str] = None,
):
    version = "0.7.6"
    if not contract.endswith(".sol"):
        contract += ".sol"
    if contract_name is None:
        if "/" in contract:
            contract_name = contract.rsplit("/", 1)[1].rsplit(".", 1)[0]
        else:
            contract_name = contract.rsplit(".", 1)[0]

    solcx.install_solc(version)

    contract_path = (pathlib.Path.cwd() / "contracts" / "neon_evm" / f"{contract}").absolute()
    if not contract_path.exists():
        contract_path = (pathlib.Path.cwd() / "contracts" / "external" / f"{contract}").absolute()

    assert contract_path.exists(), f"Can't found contract: {contract_path}"

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=version,
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
    user: Caller,
    contract_file_name: tp.Union[pathlib.Path, str],
    contract_name: tp.Optional[str] = None,
    encoded_args=None,
    gas: int = 999999999,
    chain_id=111,
    access_list=None,
) -> SignedTransaction:
    data = get_contract_bin(contract_file_name, contract_name)
    if encoded_args is not None:
        data = data + encoded_args.hex()

    nonce = EvmLoader(user.solana_account).get_neon_nonce(user.eth_address)
    tx = {"to": None, "value": 0, "gas": gas, "gasPrice": 0, "nonce": nonce, "data": data}
    if chain_id:
        tx["chainId"] = chain_id
    if access_list:
        tx["accessList"] = access_list
        tx["type"] = 1

    return w3.eth.account.sign_transaction(tx, user.solana_account.secret_key[:32])


def make_contract_call_trx(
    user, contract, function_signature, params=None, value=0, chain_id=111, access_list=None, trx_type=None
):
    # does not work for tuple in params
    data = abi.function_signature_to_4byte_selector(function_signature)

    if params is not None:
        types = function_signature.split("(")[1].split(")")[0].split(",")
        data += eth_abi.encode(types, params)

    signed_tx = make_eth_transaction(
        contract.eth_address, data, user, value=value, chain_id=chain_id, access_list=access_list, type=trx_type
    )
    return signed_tx


def deploy_contract(
    operator: Keypair,
    user: Caller,
    contract_file_name: tp.Union[pathlib.Path, str],
    evm_loader: EvmLoader,
    treasury_pool: TreasuryPool,
    step_count: int = 1000,
    encoded_args=None,
    contract_name: tp.Optional[str] = None,
):
    print("Deploying contract")
    contract: Contract = create_contract_address(user, evm_loader)
    holder_acc = create_holder(operator)
    signed_tx = make_deployment_transaction(user, contract_file_name, contract_name, encoded_args=encoded_args)
    write_transaction_to_holder_account(signed_tx, holder_acc, operator)

    index = 0
    contract_deployed = False
    while not contract_deployed:
        receipt = send_transaction_step_from_account(
            operator,
            evm_loader,
            treasury_pool,
            holder_acc,
            [contract.solana_address, contract.balance_account_address, user.balance_account_address],
            step_count,
            operator,
            index=index,
        )
        index += 1

        if receipt.value.transaction.meta.err:
            raise AssertionError(f"Can't deploy contract: {receipt.value.transaction.meta.err}")
        for log in receipt.value.transaction.meta.log_messages:
            if "exit_status" in log:
                contract_deployed = True
                break
            if "ExitError" in log:
                raise AssertionError(f"EVM Return error in logs: {receipt}")
    return contract
