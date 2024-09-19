import random

import allure
import pytest
import requests
from web3 import Web3

from integration.tests.basic.helpers import rpc_checks
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC batch operations")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestBatchOperations:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    def test_batch_operations_same_function(
            self,
            request: pytest.FixtureRequest,
            common_contract,
    ):
        """
        sends a batch operation request with 100 calls to the same function with different parameters
        """
        account = self.accounts[0]

        batch = []
        expected_results = []

        for id_ in range(1, 101):
            a = random.randint(0, 10000)
            b = random.randint(0, 10000)
            expected_results.append(a * b)

            function_signature = Web3.solidity_keccak(["string"], ["multiply(uint32,uint32)"]).hex()[:10]
            a_padded_hex = hex(a)[2:].zfill(64)
            b_padded_hex = hex(b)[2:].zfill(64)
            data = f"{function_signature}{a_padded_hex}{b_padded_hex}"

            batch.append(
                {
                    "id": id_,
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [
                        {
                            "from": account.address,
                            "to": common_contract.address,
                            "data": data,
                        },
                        "latest",
                    ],
                }
            )

        response = requests.post(
            url=request.config.environment.proxy_url,  # noqa
            json=batch,
        )

        results = response.json()
        msg = f"Sent batch length {len(expected_results)}, but received {len(results)} results"
        assert len(results) == len(expected_results), msg

        for index, result in enumerate(results):
            assert "error" not in result
            assert result["id"] == index + 1, f"Batch response response sequence invalid"

            result_hex = result["result"]
            actual_function_return = int(result_hex, 16)
            expected_function_return = expected_results[index]
            assert actual_function_return == expected_function_return, "Invalid function return"

    def test_batch_operations_different_functions(
            self,
            request: pytest.FixtureRequest,
    ):
        """
        sends a batch operation request with a few calls to different functions
        """
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, estimate_gas=True
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)

        batch = [
            {
                "jsonrpc": "2.0",
                "method": "eth_chainId",
                "params": [],
                "id": 1,
            },
            {
                "jsonrpc": "2.0",
                "method": "eth_gasPrice",
                "params": [],
                "id": 2,
            },
            {
                "jsonrpc": "2.0",
                "method": "eth_sendRawTransaction",
                "params": [signed_tx.rawTransaction.hex()],
                "id": 3,
            },
        ]

        response = requests.post(
            url=request.config.environment.proxy_url,  # noqa
            json=batch,
        )

        results = response.json()
        msg = f"Sent batch length {len(batch)}, but received {len(results)} results"
        assert len(results) == len(batch), msg

        for result in results:
            assert "error" not in result
            assert rpc_checks.is_hex(result["result"])

    def test_batch_operations_negative(
            self,
            request: pytest.FixtureRequest,
            common_contract,
    ):
        """
        sends a batch operation request with a few calls with invalid parameters
        """
        account = self.accounts[0]

        function_signature = Web3.solidity_keccak(["string"], ["setNumber(uint256)"]).hex()[:10]
        invalid_number_hex = hex(1000)[2:].zfill(64)[1:]
        data = f"{function_signature}{invalid_number_hex}"

        batch = [
            {
                "jsonrpc": "2.0",
                "method": "eth_sendRawTransaction",
                "params": ["invalid params"],
                "id": 1,
            },
            {
                "jsonrpc": "2.0",
                "method": "invalid_method_name",
                "params": [],
                "id": 2,
            },
            {
                "id": 3,
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [
                    {
                        "from": account.address,
                        "to": common_contract.address,
                        "data": data,
                    },
                    "latest",
                ],
            }
        ]

        response = requests.post(
            url=request.config.environment.proxy_url,  # noqa
            json=batch,
        )

        results = response.json()
        msg = f"Sent batch length {len(batch)}, but received {len(results)} results"
        assert len(results) == len(batch), msg

        for result in results:
            assert "error" in result

    def test_batch_operations_positive_and_negative_mix(
            self,
            request: pytest.FixtureRequest,
    ):
        """
        sends a batch operation request with a mix of positive and calls to different functions
        """
        batch = [
            {
                "jsonrpc": "2.0",
                "method": "eth_chainId",
                "params": [],
                "id": 1,
            },
            {
                "jsonrpc": "2.0",
                "method": "eth_gasPrice",
                "params": [],
                "id": 2,
            },
            {
                "jsonrpc": "2.0",
                "method": "invalid_method_name",
                "params": [],
                "id": 3,
            },
            {
                "jsonrpc": "2.0",
                "method": "eth_mining",
                "params": [],
                "id": 4,
            },
            {
                "jsonrpc": "2.0",
                "method": "eth_syncing",
                "params": [],
                "id": 5,
            },

        ]

        response = requests.post(
            url=request.config.environment.proxy_url,  # noqa
            json=batch,
        )

        results = response.json()
        msg = f"Sent batch length {len(batch)}, but received {len(results)} results"
        assert len(results) == len(batch), msg

        for result in results:
            result_id = result["id"]
            if result_id == 3:
                assert "error" in result
            else:
                assert "error" not in result
