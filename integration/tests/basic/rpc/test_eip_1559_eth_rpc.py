import allure
import pytest

from clickfile import EnvName
from utils.accounts import EthAccounts
from utils.apiclient import JsonRPCSession
from utils.web3client import NeonChainWeb3Client


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify new fields in eth_ JSON-RPC methods")
@pytest.mark.neon_only
class TestRpcEthMethods:
    def test_get_transaction_by_hash(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,

    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByHash",
            params=[receipt.transactionHash.hex()],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    def test_get_transaction_by_block_hash_and_index(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,

    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        transaction_index = hex(receipt.transactionIndex)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockHashAndIndex",
            params=[receipt.blockHash.hex(), transaction_index],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    def test_get_transaction_by_block_number_and_index(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_number = hex(receipt.blockNumber)
        index = hex(receipt.transactionIndex)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[block_number, index],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    @pytest.mark.neon_only
    @pytest.mark.parametrize(
        argnames="full_transaction_objects",
        argvalues=(True, False),
    )
    def test_get_block_by_hash(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
            full_transaction_objects: bool,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_from_history = web3_client.base_fee_per_gas()
        base_fee_per_gas = base_fee_from_history * 2
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = base_fee_per_gas + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_hash = receipt.blockHash.hex()
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByHash",
            params=[block_hash, full_transaction_objects],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None

        block_base_fee = int(result['baseFeePerGas'], 16)
        assert block_base_fee <= base_fee_per_gas

    @pytest.mark.neon_only
    @pytest.mark.parametrize(
        argnames="full_transaction_objects",
        argvalues=(True, False),
    )
    def test_get_block_by_number(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
            full_transaction_objects: bool,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_from_history = web3_client.base_fee_per_gas()
        base_fee_per_gas = base_fee_from_history * 2
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=base_fee_per_gas + max_priority_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_number = hex(receipt.blockNumber)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByNumber",
            params=[block_number, full_transaction_objects],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None

        block_base_fee = int(result['baseFeePerGas'], 16)

        assert block_base_fee <= base_fee_per_gas

    def test_get_transaction_receipt(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            env_name: EnvName,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = 2 * base_fee_per_gas + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        actual_effective_gas_price = receipt.effectiveGasPrice
        if env_name is EnvName.GETH:
            expected_effective_gas_price = min(max_fee_per_gas, base_fee_per_gas + max_priority_fee_per_gas)
        else:
            expected_effective_gas_price = max_fee_per_gas
        assert actual_effective_gas_price == expected_effective_gas_price
