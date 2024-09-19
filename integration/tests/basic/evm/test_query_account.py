import random

import base58
import pytest
from solders.pubkey import Pubkey
from web3.contract import Contract
from solders.keypair import Keypair

from utils.accounts import EthAccounts
from utils.helpers import wait_condition
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


class TestQueryAccountLib:
    # ---------------------------------------- owner ----------------------------------------
    def test_owner_positive(
        self,
        query_account_caller_contract: Contract,
        solana_account: Keypair,
        sol_client_session: SolanaClient,
    ):
        new_solana_account = sol_client_session.create_account(
            payer=solana_account,
            size=0,
            owner=solana_account.pubkey(),
        )

        solana_account_address_uint256 = int.from_bytes(new_solana_account.pubkey(), byteorder="big")

        success, actual_owner_address = query_account_caller_contract.functions.queryOwner(
            solana_account_address_uint256
        ).call()

        expected_owner_address = int.from_bytes(solana_account.pubkey(), byteorder="big")
        assert success is True
        assert actual_owner_address == expected_owner_address

    def test_owner_through_transaction_positive(
            self,
            accounts: EthAccounts,
            sol_client_session: SolanaClient,
            solana_account: Keypair,
            query_account_caller_contract: Contract,
            web3_client: NeonChainWeb3Client,
    ):
        account = accounts[0]
        new_solana_account = sol_client_session.create_account(
            payer=solana_account,
            size=0,
            owner=solana_account.pubkey(),
        )

        solana_account_address_uint256 = int.from_bytes(new_solana_account.pubkey(), byteorder="big")
        tx = web3_client.make_raw_tx(account)

        instruction_tx = query_account_caller_contract.functions.queryOwner(
            solana_account_address_uint256
        ).build_transaction(tx)

        tx_receipt = web3_client.send_transaction(account, instruction_tx)
        log_raw = tx_receipt.logs[0]
        log_processed = query_account_caller_contract.events.QueryResultUint256().process_log(log_raw)
        success = log_processed.args.success
        actual_owner_address = log_processed.args.result
        expected_owner_address = int.from_bytes(solana_account.pubkey(), byteorder="big")

        assert success is True
        assert actual_owner_address == expected_owner_address

    def test_owner_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, actual_owner_address = query_account_caller_contract.functions.queryOwner(
            max_non_existent_solana_address
        ).call()

        assert success is True
        assert actual_owner_address == 0

    # ---------------------------------------- length ----------------------------------------
    def test_length_positive(
        self,
        query_account_caller_contract: Contract,
        solana_account: Keypair,
        sol_client_session: SolanaClient,
    ):
        expected_length = random.randint(0, 10000)
        new_solana_account = sol_client_session.create_account(
            payer=solana_account,
            size=expected_length,
            owner=solana_account.pubkey(),
        )

        solana_account_address_uint256 = int.from_bytes(new_solana_account.pubkey(), byteorder="big")

        success, actual_length = query_account_caller_contract.functions.queryLength(
            solana_account_address_uint256
        ).call()

        assert success is True
        assert actual_length == expected_length

    def test_length_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, actual_owner_address = query_account_caller_contract.functions.queryLength(
            max_non_existent_solana_address
        ).call()

        assert success is True
        assert actual_owner_address == 0

    # ---------------------------------------- lamports ----------------------------------------
    def test_lamports_positive(
        self,
        query_account_caller_contract: Contract,
        solana_account: Keypair,
        sol_client_session: SolanaClient,
    ):
        size = random.randint(0, 1000)
        minimum_lamports = sol_client_session.get_minimum_balance_for_rent_exemption(size).value
        expected_lamports_before = minimum_lamports + random.randint(1000, 10000)
        new_solana_account = sol_client_session.create_account(
            payer=solana_account,
            size=size,
            owner=solana_account.pubkey(),
            lamports=expected_lamports_before,
        )

        solana_account_address_uint256 = int.from_bytes(new_solana_account.pubkey(), byteorder="big")

        success, actual_lamports_before = query_account_caller_contract.functions.queryLamports(
            solana_account_address_uint256
        ).call()

        assert success is True
        assert actual_lamports_before == expected_lamports_before

        additional_lamports = random.randint(0, 1000)
        sol_client_session.request_airdrop(pubkey=new_solana_account.pubkey(), lamports=additional_lamports)
        expected_lamports_after = expected_lamports_before + additional_lamports

        success, actual_lamports_after = query_account_caller_contract.functions.queryLamports(
            solana_account_address_uint256
        ).call()

        assert success is True
        assert actual_lamports_after == expected_lamports_after

    def test_lamports_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, actual_owner_address = query_account_caller_contract.functions.queryLamports(
            max_non_existent_solana_address
        ).call()

        assert success is True
        assert actual_owner_address == 0

    # ---------------------------------------- executable ----------------------------------------
    def test_executable_true(
        self,
        request: pytest.FixtureRequest,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        evm_loader_address_base58 = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        success, is_executable = query_account_caller_contract.functions.queryExecutable(
            solana_account_address_uint256
        ).call()

        assert success is True
        assert is_executable is True

    def test_executable_false(
        self,
        query_account_caller_contract: Contract,
        solana_account: Keypair,
        sol_client_session: SolanaClient,
    ):
        solana_account_address_uint256 = int.from_bytes(solana_account.pubkey(), byteorder="big")

        success, is_executable = query_account_caller_contract.functions.queryExecutable(
            solana_account_address_uint256
        ).call()

        assert success is True
        assert is_executable is False

    def test_executable_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, actual_owner_address = query_account_caller_contract.functions.queryExecutable(
            max_non_existent_solana_address
        ).call()

        assert success is True
        assert actual_owner_address == 0

    # ---------------------------------------- rent epoch ----------------------------------------
    def test_rent_epoch_positive(
        self,
        solana_account: Keypair,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        solana_account_address_uint256 = int.from_bytes(solana_account.pubkey(), byteorder="big")

        success, rent_epoch_actual = query_account_caller_contract.functions.queryRentEpoch(
            solana_account_address_uint256
        ).call()

        assert success is True

        wait_condition(
            func_cond=lambda: sol_client_session.get_account_info(solana_account.pubkey()).value is not None,
        )
        account_info = sol_client_session.get_account_info(solana_account.pubkey())
        rent_epoch_expected = account_info.value.rent_epoch
        assert rent_epoch_actual == rent_epoch_expected

    def test_rent_epoch_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, actual_rent_epoch = query_account_caller_contract.functions.queryRentEpoch(
            max_non_existent_solana_address
        ).call()

        assert success is True
        assert actual_rent_epoch == 0

    # ---------------------------------------- data ----------------------------------------
    def test_data_positive(
        self,
        request: pytest.FixtureRequest,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        evm_loader_address_base58: str = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        evm_loader_public_key = Pubkey(evm_loader_address)
        length = len(sol_client_session.get_account_info(evm_loader_public_key).value.data)

        success, actual_data = query_account_caller_contract.functions.queryData(
            solana_account_address_uint256,
            0,
            length,
        ).call()

        assert success is True
        assert "error" not in actual_data.decode("utf-8", errors="ignore").lower()

        account_info = sol_client_session.get_account_info(evm_loader_public_key)
        expected_data = account_info.value.data
        assert actual_data == expected_data

    def test_data_through_transaction_positive(
            self,
            request: pytest.FixtureRequest,
            query_account_caller_contract: Contract,
            sol_client_session: SolanaClient,
            web3_client: NeonChainWeb3Client,
            accounts: EthAccounts,
    ):
        evm_loader_address_base58 = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        evm_loader_public_key = Pubkey(evm_loader_address)
        length = len(sol_client_session.get_account_info(evm_loader_public_key).value.data)

        account = accounts[0]
        tx = web3_client.make_raw_tx(account)

        instruction_tx = query_account_caller_contract.functions.queryData(
            solana_account_address_uint256,
            0,
            length,
        ).build_transaction(tx)

        tx_receipt = web3_client.send_transaction(account, instruction_tx)
        log_raw = tx_receipt.logs[0]
        log_processed = query_account_caller_contract.events.QueryResultBytes().process_log(log_raw)
        success = log_processed.args.success
        actual_data = log_processed.args.result

        account_info = sol_client_session.get_account_info(evm_loader_public_key)
        expected_data = account_info.value.data

        assert success is True
        assert actual_data == expected_data

    def test_data_negative_address_max_int(
        self,
        query_account_caller_contract: Contract,
        max_non_existent_solana_address: int,
    ):
        success, data = query_account_caller_contract.functions.queryData(
            max_non_existent_solana_address,
            0,
            1,
        ).call()

        assert success is False
        assert "out of bounds" in data.decode("utf-8", errors="ignore").lower()

    def test_data_negative_invalid_offset(
        self,
        request: pytest.FixtureRequest,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        evm_loader_address_base58 = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        length = len(sol_client_session.get_account_info(Pubkey(evm_loader_address)).value.data)

        success, data = query_account_caller_contract.functions.queryData(
            solana_account_address_uint256,
            length,
            length,
        ).call()

        assert success is False
        assert "out of bounds" in data.decode("utf-8", errors="ignore").lower()

    def test_data_negative_length_zero(
        self,
        request: pytest.FixtureRequest,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        evm_loader_address_base58 = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        success, data = query_account_caller_contract.functions.queryData(
            solana_account_address_uint256,
            0,
            0,
        ).call()

        assert success is False

        length_bytes = data.split(b"length == ")[-1]
        actual_length = int(length_bytes.decode().rstrip("\x00"))
        assert actual_length == 0

    def test_data_negative_invalid_length(
        self,
        request: pytest.FixtureRequest,
        query_account_caller_contract: Contract,
        sol_client_session: SolanaClient,
    ):
        evm_loader_address_base58 = request.config.environment.evm_loader  # noqa
        evm_loader_address = base58.b58decode(evm_loader_address_base58)
        solana_account_address_uint256 = int.from_bytes(evm_loader_address, byteorder="big")

        length = len(sol_client_session.get_account_info(Pubkey(evm_loader_address)).value.data)

        success, data = query_account_caller_contract.functions.queryData(
            solana_account_address_uint256,
            0,
            length + 1,
        ).call()

        assert success is False
        assert "out of bounds" in data.decode("utf-8", errors="ignore").lower()
