import pytest

import allure
from clickfile import EnvName
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32602
from utils.accounts import EthAccounts
from utils.apiclient import JsonRPCSession
from utils.helpers import gen_hash_of_block
from utils.models.error import EthError32602
from utils.models.result import EthGetBlockByHashResult, EthGetBlockByHashFullResult
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify getBlock methods")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcGetBlock:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.mainnet
    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash(
        self,
        full_trx: bool,
        json_rpc_client: JsonRPCSession,
        env_name: EnvName,
    ):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 1)
        params = [tx_receipt.blockHash.hex(), full_trx]
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=params)
        rpc_checks.assert_block_fields(
            env_name=env_name,
            response=response,
            full_trx=full_trx,
            tx_receipt=tx_receipt,
        )
        if full_trx:
            EthGetBlockByHashFullResult(**response)
        else:
            EthGetBlockByHashResult(**response)

    @pytest.mark.parametrize(
        "hash_len, full_trx",
        [(31, False), ("bad_hash", True)],
    )
    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    def test_eth_get_block_by_hash_with_incorrect_hash(self, hash_len, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        block_hash = gen_hash_of_block(hash_len) if isinstance(hash_len, int) else hash_len
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[block_hash, full_trx])
        EthError32602(**response)
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == Error32602.CODE
        assert response["error"]["message"] == Error32602.INVALID_BLOCKHASH

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash_with_not_existing_hash(self, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[gen_hash_of_block(32), full_trx])
        assert "result" in response and response["result"] is None, "Result should be None"
        EthGetBlockByHashResult(**response)

    @pytest.mark.mainnet
    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_via_numbers(
        self,
        full_trx: bool,
        json_rpc_client: JsonRPCSession,
        env_name: EnvName,
    ):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 1)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByNumber",
            params=[hex(tx_receipt.blockNumber), full_trx],
        )
        rpc_checks.assert_block_fields(
            env_name=env_name,
            response=response,
            full_trx=full_trx,
            tx_receipt=tx_receipt,
        )
        if full_trx:
            EthGetBlockByHashFullResult(**response)
        else:
            EthGetBlockByHashResult(**response)

    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    def test_eth_get_block_by_number_with_incorrect_data(self, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=["bad_tag", True])
        EthError32602(**response)
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == Error32602.CODE
        assert response["error"]["message"] == Error32602.INVALID_PARAMETERS

    @pytest.mark.parametrize(
        "number, full_trx",
        [
            (8, True),
            (8, False),
        ],
    )
    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    def test_eth_get_block_by_number_with_not_exist_data(self, number, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=[gen_hash_of_block(number), full_trx])
        EthGetBlockByHashResult(**response)
        assert "result" in response and response["result"] is None, "Result should be None"

    @pytest.mark.xfail(
        reason="NDEV-3072"
    )  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_with_big_int(self, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByNumber",
            params=["0x55192d7d9e36433b64f2b9d9309a5c5d36b1561c888dcfa8f31078f000fa7cdd", full_trx],
        )
        EthError32602(**response)

    @pytest.mark.parametrize(
        "quantity_tag, full_trx",
        [
            (Tag.EARLIEST, True),
            (Tag.EARLIEST, False),
            (Tag.LATEST, True),
            (Tag.LATEST, False),
            (Tag.PENDING, True),
            (Tag.PENDING, False),
        ],
    )
    def test_eth_get_block_by_number_via_tags(
        self,
        quantity_tag: Tag,
        full_trx: bool,
        json_rpc_client: JsonRPCSession,
        env_name: EnvName,
    ):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.web3_client.send_neon(sender_account, recipient_account, 1)
        params = [quantity_tag.value, full_trx]
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=params)
        rpc_checks.assert_block_fields(
            env_name=env_name,
            response=response,
            full_trx=full_trx,
            tx_receipt=None,
            pending=quantity_tag == Tag.PENDING,
        )
        if full_trx:
            EthGetBlockByHashFullResult(**response)
        else:
            EthGetBlockByHashResult(**response)
