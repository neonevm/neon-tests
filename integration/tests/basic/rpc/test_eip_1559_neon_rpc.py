import allure
import pytest

from utils.accounts import EthAccounts
from utils.apiclient import JsonRPCSession
from utils.web3client import NeonChainWeb3Client


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify new fields in neon_ JSON-RPC methods")
@pytest.mark.neon_only
class TestRpcNeonMethods:

    def test_neon_get_transaction_by_sender_nonce(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]
        nonce = web3_client.get_nonce(address=sender.address)
        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        response = json_rpc_client.send_rpc(
            method="neon_getTransactionBySenderNonce", params=[sender.address, nonce]
        )

        assert "error" not in response, response["error"]
        max_priority_fee_per_gas_response = response["result"].get("maxPriorityFeePerGas")
        assert max_priority_fee_per_gas_response is not None
        assert int(max_priority_fee_per_gas_response, 16) == max_priority_fee_per_gas

        max_fee_per_gas_response = response["result"].get("maxFeePerGas")
        assert max_fee_per_gas is not None
        assert int(max_fee_per_gas_response, 16) == max_fee_per_gas

    def test_neon_get_solana_transaction_by_neon_transaction(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
        )
        params = [receipt.transactionHash.hex()]
        response = json_rpc_client.send_rpc(method="neon_getSolanaTransactionByNeonTransaction", params=params)

        assert "error" not in response, response["error"]
        hash_solana = response["result"]
        assert hash_solana

    def test_neon_get_transaction_receipt(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            max_fee_per_gas=max_fee_per_gas,
        )

        params = [receipt.transactionHash.hex()]
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=params)

        assert "error" not in response, response["error"]

        actual_effective_gas_price = int(response["result"].get("effectiveGasPrice"), 16)
        assert actual_effective_gas_price >= base_fee_per_gas
        assert actual_effective_gas_price <= max_fee_per_gas
