import hashlib
import json
import logging
import pathlib
from typing import TypedDict

import allure
import eth_abi
import pytest
from eth_account.datastructures import SignedTransaction
from eth_utils import to_checksum_address
from solana.rpc.commitment import Confirmed, Finalized
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.responses import GetTransactionResp

from integration.tests.basic.evm.test_spl_token import DECIMALS, NAME, SYMBOL
from integration.tests.neon_evm.conftest import prepare_operator
from integration.tests.neon_evm.utils.ethereum import make_eth_transaction, make_contract_call_trx
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.consts import LAMPORT_PER_SOL, NeonTxExitStatus, OPERATOR_KEYPAIR_PATH
from utils.evm_loader import EvmLoader, EVM_STEPS
from utils.helpers import decode_function_signature
from utils.metaplex import create_metadata_instruction_data, create_metadata_instruction
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction
from utils.solana_client import SolanaClient
from utils.types import Caller, TreasuryPool

logger = logging.getLogger(__name__)


deterministic_index_of_process_stash_key = pytest.StashKey[set]()
deterministic_sender_with_tokens_index_stash_key = pytest.StashKey[set]()
deterministic_user_index_stash_key = pytest.StashKey[set]()
deterministic_holder_acc_seed_stash_key = pytest.StashKey[set]()


class DeterministicKeyPairs(TypedDict):
    sender_with_tokens: list[Keypair]
    user: list[Keypair]


def get_and_validate_mark_value(
    request: pytest.FixtureRequest,
    key: pytest.StashKey[set],
    mark: str,
) -> int:
    """
    Gets the closest mark value and makes sure it's unique
    """
    passed_value = request.node.get_closest_marker(mark).args[0]
    used_values = request.config.stash.get(key, set())

    if passed_value in used_values:
        raise Exception(f"{mark}({passed_value}) was already used in another test")

    used_values.add(passed_value)
    request.config.stash[key] = used_values

    return passed_value


def skip_if_non_zero_balance(*pub_keys: Pubkey, evm_loader: EvmLoader):
    for key in pub_keys:
        balance = evm_loader.get_solana_balance(key)

        if balance != 0:
            pytest.skip(f"{key} has non-zero balance")


@pytest.fixture
def deterministic_index_of_process(request: pytest.FixtureRequest) -> int:
    """
    the process index must NOT overlap with indices used by fixtures:
         from integration.tests.neon_evm.conftest import (
             operator_keypair,
             second_operator_keypair,
         )
    """
    process_index = get_and_validate_mark_value(
        request=request, key=deterministic_index_of_process_stash_key, mark="deterministic_index_of_process"
    )
    assert 15 <= process_index <= 21, "Use values from 15 to 21"
    return process_index


@pytest.fixture(scope="session")
def deterministic_key_pairs() -> DeterministicKeyPairs:
    pairs: list[Keypair] = []
    count = 20

    for i in range(count):
        seed_bytes = hashlib.sha256(f"Seed_{i}".encode()).digest()
        keypair = Keypair.from_seed(seed_bytes[:32])
        pairs.append(keypair)

    mid_index = count // 2

    key_pairs: DeterministicKeyPairs = {
        "sender_with_tokens": [pairs[i] for i in range(mid_index)],
        "user": [pairs[i] for i in range(mid_index, count)],
    }
    return key_pairs


@pytest.fixture
def deterministic_operator_keypair(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_index_of_process: int,
    deterministic_key_pairs: DeterministicKeyPairs,
) -> Keypair:
    key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{deterministic_index_of_process}.json")

    with open(key_file, "r") as key:
        secret_key = json.load(key)
        key_pair = Keypair.from_bytes(secret_key)

    skip_if_non_zero_balance(key_pair.pubkey(), evm_loader=evm_loader)
    return prepare_operator(key_file, evm_loader)


@pytest.fixture
def deterministic_treasury_pool(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_index_of_process: int,
) -> TreasuryPool:
    index = deterministic_index_of_process
    evm_loader.create_treasury_pool_address(index)
    address = evm_loader.create_treasury_pool_address(index)
    index_buf = index.to_bytes(4, "little")
    evm_loader.request_airdrop(address, 5 * LAMPORT_PER_SOL, commitment=Confirmed)
    return TreasuryPool(index, address, index_buf)


@pytest.fixture
def deterministic_sender_with_tokens(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_operator_keypair: Keypair,
    deterministic_key_pairs: DeterministicKeyPairs,
) -> Caller:
    index = get_and_validate_mark_value(
        request=request,
        key=deterministic_sender_with_tokens_index_stash_key,
        mark="deterministic_sender_with_tokens_index",
    )
    key_pair = deterministic_key_pairs["sender_with_tokens"][index]

    skip_if_non_zero_balance(key_pair.pubkey(), evm_loader=evm_loader)

    user = evm_loader.make_new_user(deterministic_operator_keypair, key_pair=key_pair)
    evm_loader.deposit_neon(deterministic_operator_keypair, user.eth_address, 10000000)
    return user


@pytest.fixture
def deterministic_user(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_operator_keypair: Keypair,
    deterministic_key_pairs: DeterministicKeyPairs,
) -> Caller:
    index = get_and_validate_mark_value(
        request=request, key=deterministic_user_index_stash_key, mark="deterministic_user_index"
    )
    key_pair = deterministic_key_pairs["user"][index]

    skip_if_non_zero_balance(key_pair.pubkey(), evm_loader=evm_loader)

    return evm_loader.make_new_user(deterministic_operator_keypair, key_pair=key_pair)


@pytest.fixture
def deterministic_holder_acc(
    request: pytest.FixtureRequest, deterministic_operator_keypair: Keypair, evm_loader: EvmLoader
) -> Pubkey:
    seed_int = get_and_validate_mark_value(
        request=request, key=deterministic_holder_acc_seed_stash_key, mark="deterministic_holder_acc_seed"
    )
    seed = f"{seed_int}_seed"

    pubkey = Pubkey.from_bytes(
        hashlib.sha256(
            bytes(deterministic_operator_keypair.pubkey()) + bytes(seed, "utf8") + bytes(evm_loader.loader_id)
        ).digest()
    )
    skip_if_non_zero_balance(pubkey, evm_loader=evm_loader)

    return evm_loader.create_holder(signer=deterministic_operator_keypair, seed=seed)


def allure_attach_accounts_data(
    resp: GetTransactionResp,
    evm_loader: EvmLoader,
    title: str = "Used accounts data",
):
    data = {
        "signatures": [str(s) for s in resp.value.transaction.transaction.signatures],
        "cu_consumed": resp.value.transaction.meta.compute_units_consumed,
        "accounts_data": {},
    }

    for pubkey in resp.value.transaction.transaction.message.account_keys:
        info = evm_loader.get_account_info(pubkey).value

        if info:
            data["accounts_data"][str(pubkey)] = str(info.data)

    allure.attach(
        body=json.dumps(obj=data, indent=2),
        name=title,
        attachment_type=allure.attachment_type.JSON,
    )


@allure.step("Execute transaction steps from instruction and validate compute units")
def execute_transaction_steps_from_instruction_and_validate_cu(
    evm_loader: EvmLoader,
    operator: Keypair,
    treasury,
    storage_account,
    instruction: SignedTransaction,
    additional_accounts,
    cu_expected_list: list[int],
    cu_delta_allowed: int,
    sol_client: SolanaClient,
    expect_log: str,
    signer: Keypair = None,
    compute_unit_price=None,
    chain_id: int | None = None,
):
    chain_id = chain_id or evm_loader.chain_id

    signer = operator if signer is None else signer
    operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator, chain_id)
    index = 0
    done = False

    while not done:
        receipt = evm_loader.send_transaction_step_from_instruction(
            operator,
            operator_balance_pubkey,
            treasury,
            storage_account,
            instruction,
            additional_accounts,
            EVM_STEPS,
            signer,
            compute_unit_price=compute_unit_price,
            index=index,
        )
        if receipt.value.transaction.meta.err:
            raise AssertionError(f"Transaction failed with error: {receipt.value.transaction.meta.err}")
        for log in receipt.value.transaction.meta.log_messages:
            if "exit_status" in log:
                done = True
                break
            if "ExitError" in log:
                raise AssertionError(f"EVM Returned an error in logs: {receipt}")

        allure_attach_accounts_data(resp=receipt, evm_loader=evm_loader, title=f"Used accounts data {index}")

        cu_consumed = receipt.value.transaction.meta.compute_units_consumed
        cu_expected = cu_expected_list[index]
        assert (
            cu_consumed - cu_expected
        ) <= cu_delta_allowed, (
            f"CU consumed {cu_consumed} is not in range of expected {cu_expected} +/- {cu_delta_allowed}"
        )
        index += 1

    check_transaction_logs_have_text(solana_client=sol_client, trx=receipt, text=expect_log)  # noqa


class TestComputeUnits:
    @pytest.mark.deterministic_index_of_process(15)
    @pytest.mark.deterministic_sender_with_tokens_index(0)
    @pytest.mark.deterministic_user_index(0)
    @pytest.mark.deterministic_holder_acc_seed(0)
    def test_simple_transfer(
        self,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_sender_with_tokens: Caller,
        deterministic_user: Caller,
        evm_loader: EvmLoader,
        deterministic_holder_acc: Pubkey,
        sol_client: SolanaClient,
    ):
        signed_tx = make_eth_transaction(
            evm_loader=evm_loader,
            to_addr=deterministic_user.eth_address,
            data=None,
            caller=deterministic_sender_with_tokens,
            value=10,
            gas=10000,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator=deterministic_operator_keypair,
            holder_acc=deterministic_holder_acc,
            treasury_address=deterministic_treasury_pool.account,
            treasury_buffer=deterministic_treasury_pool.buffer,
            instruction=signed_tx,
            additional_accounts=[
                deterministic_sender_with_tokens.balance_account_address,
                deterministic_user.balance_account_address,
                deterministic_user.solana_account_address,
            ],
            compute_unit_price=1000,
        )
        assert resp.value.transaction.meta.err is None
        check_transaction_logs_have_text(
            solana_client=sol_client,
            trx=resp,
            text=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert abs(cu_consumed - 79302) <= 1000

    @pytest.mark.deterministic_index_of_process(16)
    @pytest.mark.deterministic_user_index(1)
    @pytest.mark.deterministic_holder_acc_seed(1)
    def test_iterative_with_many_accounts(
        self,
        deterministic_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
    ):
        rw_lock = evm_loader.deploy_contract(
            deterministic_operator_keypair, deterministic_user, "rw_lock", neon_api_client, deterministic_treasury_pool
        )

        constructor_args = eth_abi.encode(["address"], [rw_lock.eth_address.hex()])
        rw_lock_caller_contract = evm_loader.deploy_contract(
            deterministic_operator_keypair,
            deterministic_user,
            "rw_lock",
            neon_api_client,
            deterministic_treasury_pool,
            encoded_args=constructor_args,
            contract_name="rw_lock_caller",
        )

        signed_eth_tx = make_contract_call_trx(
            evm_loader, deterministic_user, rw_lock_caller_contract, "update_storage_map(uint256)", [15]
        )

        data = decode_function_signature("update_storage_map(uint256)", [15])
        emulate_result = neon_api_client.emulate(
            deterministic_user.eth_address.hex(), rw_lock_caller_contract.eth_address.hex(), data[2:]
        )
        additional_accounts = [Pubkey.from_string(acc["pubkey"]) for acc in emulate_result["solana_accounts"]]

        execute_transaction_steps_from_instruction_and_validate_cu(
            evm_loader=evm_loader,
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_eth_tx,
            additional_accounts=additional_accounts,
            cu_expected_list=[85726, 97192, 61008, 180406],
            cu_delta_allowed=1000,
            sol_client=sol_client,
            expect_log=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

    @pytest.mark.deterministic_index_of_process(17)
    @pytest.mark.deterministic_user_index(2)
    @pytest.mark.deterministic_holder_acc_seed(2)
    @pytest.mark.deterministic_sender_with_tokens_index(2)
    def test_payable_function(
        self,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_sender_with_tokens: Caller,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
    ):
        contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_sender_with_tokens,
            contract_file_name="string_setter",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
        )
        function_signature = "set(string)"
        params = ["Hello"]
        value = 100
        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_sender_with_tokens,
            contract=contract,
            function_signature=function_signature,
            params=params,
            value=value,
        )

        data = decode_function_signature(function_signature, params)
        emulate_result = neon_api_client.emulate(
            sender=deterministic_sender_with_tokens.eth_address.hex(),
            contract=contract.eth_address.hex(),
            data=data[2:],
            value=hex(value),
        )
        additional_accounts = [Pubkey.from_string(acc["pubkey"]) for acc in emulate_result["solana_accounts"]]

        execute_transaction_steps_from_instruction_and_validate_cu(
            evm_loader=evm_loader,
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_tx,
            additional_accounts=additional_accounts,
            cu_expected_list=[77761, 52641, 50370],
            cu_delta_allowed=1000,
            sol_client=sol_client,
            expect_log=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

    @pytest.mark.deterministic_index_of_process(18)
    @pytest.mark.deterministic_user_index(3)
    @pytest.mark.deterministic_holder_acc_seed(3)
    def test_nested_calls(
        self,
        deterministic_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
    ):
        contract_a = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_user,
            contract_file_name="common/NestedCallsChecker",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="A",
            version="0.8.12",
        )
        contract_b = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_user,
            contract_file_name="common/NestedCallsChecker",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="B",
            version="0.8.12",
        )
        contract_c = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_user,
            contract_file_name="common/NestedCallsChecker",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="C",
            version="0.8.12",
        )

        contract_b_checksum_address = to_checksum_address("0x" + contract_b.eth_address.hex())
        contract_c_checksum_address = to_checksum_address("0x" + contract_c.eth_address.hex())

        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_user,
            contract=contract_a,
            function_signature="method1(address,address)",
            params=[
                contract_b_checksum_address,
                contract_c_checksum_address,
            ],
        )

        data = decode_function_signature(
            "method1(address,address)", [contract_b_checksum_address, contract_c_checksum_address]
        )

        emulate_result = neon_api_client.emulate(
            deterministic_user.eth_address.hex(), contract_a.eth_address.hex(), data[2:]
        )

        additional_accounts = [Pubkey.from_string(acc["pubkey"]) for acc in emulate_result["solana_accounts"]]

        execute_transaction_steps_from_instruction_and_validate_cu(
            evm_loader=evm_loader,
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_tx,
            additional_accounts=additional_accounts,
            cu_expected_list=[73829, 98581, 102339, 37365, 36346],
            cu_delta_allowed=1000,
            sol_client=sol_client,
            expect_log=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

    @pytest.mark.deterministic_index_of_process(19)
    @pytest.mark.deterministic_user_index(4)
    @pytest.mark.deterministic_holder_acc_seed(4)
    @pytest.mark.deterministic_sender_with_tokens_index(4)
    def test_precompiled(
        self,
        deterministic_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        deterministic_sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
        web3_client,
        accounts,
    ):
        token_mint, _ = sol_client.create_spl(deterministic_sender_with_tokens.solana_account, DECIMALS)
        metadata = create_metadata_instruction_data(NAME, SYMBOL)
        txn = Transaction()
        txn.add(
            create_metadata_instruction(
                data=metadata,
                update_authority=deterministic_sender_with_tokens.solana_account.pubkey(),
                mint_key=token_mint.pubkey,
                mint_authority_key=deterministic_sender_with_tokens.solana_account.pubkey(),
                payer=deterministic_sender_with_tokens.solana_account.pubkey(),
            )
        )
        metadata_signature = sol_client.send_transaction(
            txn,
            deterministic_sender_with_tokens.solana_account,
            opts=TxOpts(preflight_commitment=Finalized, skip_confirmation=False),
        ).value
        metadata_receipt = sol_client.get_transaction(metadata_signature, commitment=Finalized)
        assert metadata_receipt.value.transaction.meta.err is None

        contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_user,
            contract_file_name="precompiled/SplTokenCaller",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="SplTokenCaller",
            version="0.8.28",
        )
        function_signature = "initializeMint(uint8)"
        params = [DECIMALS]

        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_sender_with_tokens,
            contract=contract,
            function_signature=function_signature,
            params=params,
        )

        data = decode_function_signature(function_signature, params)

        emulate_result = neon_api_client.emulate(
            sender=deterministic_sender_with_tokens.eth_address.hex(),
            contract=contract.eth_address.hex(),
            data=data[2:],
        )

        additional_accounts = [Pubkey.from_string(acc["pubkey"]) for acc in emulate_result["solana_accounts"]]

        execute_transaction_steps_from_instruction_and_validate_cu(
            evm_loader=evm_loader,
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_tx,
            additional_accounts=additional_accounts,
            cu_expected_list=[71559, 57737, 48904],
            cu_delta_allowed=1000,
            sol_client=sol_client,
            expect_log=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

    @pytest.mark.deterministic_index_of_process(20)
    @pytest.mark.deterministic_sender_with_tokens_index(5)
    @pytest.mark.deterministic_holder_acc_seed(5)
    def test_scheduled_transaction(
        self,
        deterministic_sender_with_tokens: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
    ):
        deterministic_neon_user = NeonUser(
            evm_loader_id=str(evm_loader.loader_id),
            keypair=deterministic_sender_with_tokens.solana_account,
        )

        basic_contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_sender_with_tokens,
            contract_file_name="common/Common",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            version="0.8.12",
        )

        nonce = evm_loader.get_neon_nonce(
            account=deterministic_neon_user.neon_address,
            chain_id=evm_loader.sol_chain_id,
        )
        contract_data = 18
        data = decode_function_signature(
            function_name="setNumber(uint256)",
            args=[contract_data],
        )
        tx = ScheduledTransaction(
            payer=deterministic_neon_user.neon_address,
            sender=None,
            nonce=nonce,
            index=0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )
        tree_account = evm_loader.create_tree_account(
            neon_user=deterministic_neon_user,
            treasury=deterministic_treasury_pool,
            transaction=tx.encode(),
        )
        transaction_tree_data = neon_api_client.get_transaction_tree(
            address=deterministic_neon_user.neon_address.hex(),
            nonce=nonce,
        )
        assert transaction_tree_data.get_transaction_count() == 1

        evm_loader.write_transaction_to_holder_account(
            tx.encode(), deterministic_holder_acc, deterministic_operator_keypair
        )
        additional_accounts = [
            basic_contract.solana_address,
            deterministic_neon_user.get_balance_account(evm_loader.sol_chain_id),
        ]

        evm_loader.start_scheduled_trx_from_account(
            index=0,
            operator=deterministic_operator_keypair,
            holder=deterministic_holder_acc,
            tree_account=tree_account,
            additional_accounts=additional_accounts,
            chain_id=evm_loader.sol_chain_id,
        )

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(
            operator=deterministic_operator_keypair,
            chain_id=evm_loader.sol_chain_id,
        )
        cu_expected_list = [27420, 29282]
        done = False
        i = 0

        while not done:
            cu_expected = cu_expected_list[i]
            receipt = evm_loader.send_transaction_step_from_account(
                operator=deterministic_operator_keypair,
                operator_balance_pubkey=operator_balance_pubkey,
                treasury=deterministic_treasury_pool,
                storage_account=deterministic_holder_acc,
                additional_accounts=additional_accounts,
                steps_count=EVM_STEPS,
                signer=deterministic_operator_keypair,
                compute_unit_price=3929,
            )

            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Error in sol trx: {receipt}")

            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Returned an error in logs: {receipt}")

            allure_attach_accounts_data(resp=receipt, evm_loader=evm_loader, title=f"Used accounts data {i}")

            cu_consumed = receipt.value.transaction.meta.compute_units_consumed
            assert abs(cu_consumed - cu_expected) <= 1000
            i += 1

        evm_loader.finish_scheduled_trx(deterministic_operator_keypair, tree_account, deterministic_holder_acc)
        evm_loader.destroy_tree_account(deterministic_neon_user, deterministic_treasury_pool, tree_account)

        check_transaction_logs_have_text(
            solana_client=sol_client,
            trx=receipt,  # noqa
            text=f"exit_status={NeonTxExitStatus.SUCCESS_WITH_CHANGES}",
        )

    @pytest.mark.deterministic_index_of_process(21)
    @pytest.mark.deterministic_user_index(6)
    @pytest.mark.deterministic_holder_acc_seed(6)
    def test_negative(
        self,
        deterministic_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        sol_client: SolanaClient,
    ):
        contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_user,
            contract_file_name="common/ExpectedErrorsChecker",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="A",
            version="0.8.12",
        )
        function_signature = "method1"
        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_user,
            contract=contract,
            function_signature=function_signature,
        )

        data = decode_function_signature(function_signature)
        emulate_result = neon_api_client.emulate(
            sender=deterministic_user.eth_address.hex(),
            contract=contract.eth_address.hex(),
            data=data[2:],
        )
        additional_accounts = [Pubkey.from_string(acc["pubkey"]) for acc in emulate_result["solana_accounts"]]

        execute_transaction_steps_from_instruction_and_validate_cu(
            evm_loader=evm_loader,
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_tx,
            additional_accounts=additional_accounts,
            cu_expected_list=[71838, 26503, 29591],
            cu_delta_allowed=1000,
            sol_client=sol_client,
            expect_log=f"exit_status={NeonTxExitStatus.REVERT}",
        )
