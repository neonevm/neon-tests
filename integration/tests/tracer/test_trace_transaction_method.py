import pytest

from utils.helpers import decode_error_output
from utils.tracer_client import TracerClient
from utils.tracer_validator import TracerValidator
from utils.web3client import NeonChainWeb3Client
from eth_abi.abi import default_codec


@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api", "tracer_validator")
class TestTraceTransactionMethod:
    web3_client: NeonChainWeb3Client
    tracer_api: TracerClient
    tracer_validator: TracerValidator

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "static_call_tx_receipt", "expected_call_types": [("call", 1), ("staticcall", 0)]},
                id="static_call",
            ),
            pytest.param(
                {"fixture_name": "delegate_call_tx_receipt", "expected_call_types": [("call", 1), ("delegatecall", 0)]},
                id="delegate_call",
            ),
            pytest.param(
                {"fixture_name": "call_tx_receipt", "expected_call_types": [("call", 1), ("call", 0)]},
                id="call_tx_receipt",
            ),
            pytest.param(
                {"fixture_name": "static_call_tx_receipt", "expected_call_types": [("call", 1), ("staticcall", 0)]},
                id="static_call_with_events_tx_receipt",
            ),
        ],
    )
    def test_call_types(self, test_case, request):
        receipt = request.getfixturevalue(test_case["fixture_name"])
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)
        for i, (call_type, subtraces) in enumerate(test_case["expected_call_types"]):
            assert tracer_response["result"][i]["action"]["callType"] == call_type
            assert tracer_response["result"][i]["subtraces"] == subtraces

    def test_multiple_scheduled_tx(self, multiple_scheduled_tx_receipts):
        for receipt in multiple_scheduled_tx_receipts:
            tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
            tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
            self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "scheduled_tx_receipt", "description": "Scheduled transaction"},
                id="scheduled_transaction",
            ),
            pytest.param(
                {"fixture_name": "recursion_tx_receipt", "description": "Recursion transaction"}, id="recursion"
            ),
            pytest.param(
                {"fixture_name": "iteration_tx_receipt", "description": "Iterative transaction"}, id="iterative"
            ),
            pytest.param(
                {
                    "fixture_name": "iterative_tx_with_erc20_for_spl_receipt",
                    "description": "Iterative transaction with 51 contract calls",
                },
                id="iterative_erc20_spl",
            ),
            pytest.param(
                {"fixture_name": "precompile_contract_call_tx_receipt", "description": "Precompile contract call"},
                id="precompile_contract",
            ),
            pytest.param(
                {"fixture_name": "eth_precompile_contract_tx_receipt", "description": "ETH precompile contract"},
                id="eth_precompile",
            ),
            pytest.param(
                {"fixture_name": "precompiled_neon_contract_tx_receipt", "description": "Precompiled NEON contract"},
                id="neon_precompile",
            ),
            pytest.param(
                {
                    "fixture_name": "trivial_revert_tx_receipt",
                    "description": "Trivial revert",
                    "error_message": "Error(string): ('Revert Contract',)",
                },
                id="trivial_revert",
            ),
            pytest.param(
                {
                    "fixture_name": "revert_in_called_contract_tx_receipt",
                    "description": "Revert in called contract",
                    "error_message": "Error(string): ('Insufficient balance for transfer,",
                },
                id="revert_in_called_contract",
            ),
            pytest.param(
                {
                    "fixture_name": "zero_division_tx_receipt",
                    "description": "Zero division transaction",
                    "error_message": "Panic(uint256): Division or modulo by zero",
                },
                id="zero_division",
            ),
        ],
    )
    def test_transaction_types(self, test_case, request):
        """
        Test different types of transactions with tracer_transaction method.
        """
        receipt = request.getfixturevalue(test_case["fixture_name"])
        error_message = test_case.get("error_message")
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())

        if error_message:
            error = decode_error_output(tracer_response["result"][1]["result"]["output"])
            assert error_message in error, f"Expected error message '{error_message}' not found in '{error}'"

        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data, receipt)

    def test_failed_scheduled_tx(self, failed_scheduled_tx_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(failed_scheduled_tx_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(failed_scheduled_tx_receipt["transactionHash"].hex())

        error = decode_error_output(tracer_response["result"][1]["result"]["output"])
        expected_error_message = "Panic(uint256): Assertion violated or invalid enum value"
        assert error in expected_error_message

        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

    def test_reverted_iteration_tx(self, reverted_iterative_tx_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(reverted_iterative_tx_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(reverted_iterative_tx_receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        error = decode_error_output(tracer_response["result"][1]["result"]["output"])
        expected_error_message = "Revert without reason"
        assert error in expected_error_message

    def test_chain_transactions(self, chain_transactions_receipt_and_contracts):
        receipt, contracts = chain_transactions_receipt_and_contracts
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)
        # Validate subsequent "from" and "to" addresses
        expected_addresses = [
            (0, 1),  # result[1]: from addr[1][0] to addr[1][1]
            (0, 2),  # result[2]: from addr[1][0] to addr[1][2]
            (2, 3),  # result[3]: from addr[1][2] to addr[1][3]
            (2, 4),  # result[4]: from addr[1][2] to addr[1][4]
            (4, 6),  # result[5]: from addr[1][4] to addr[1][6]
            (2, 5),  # result[6]: from addr[1][2] to addr[1][5]
        ]

        for idx, (from_idx, to_idx) in enumerate(expected_addresses, start=1):
            result_action = tracer_response["result"][idx]["action"]
            expected_from = chain_transactions_receipt_and_contracts[1][from_idx].address.lower()
            expected_to = chain_transactions_receipt_and_contracts[1][to_idx].address.lower()
            assert result_action["from"].lower() == expected_from
            assert result_action["to"].lower() == expected_to

        # Expected trace structure based on the contract execution tree
        expected_traces = [
            {"trace": [], "subtraces": 2},  # Root call (Func1)
            {"trace": [0], "subtraces": 0},  # Func2 call
            {"trace": [1], "subtraces": 3},  # Func3 call
            {"trace": [1, 0], "subtraces": 0},  # Func4 call
            {"trace": [1, 1], "subtraces": 1},  # Func5 call
            {"trace": [1, 1, 0], "subtraces": 0},  # Func7 call
            {"trace": [1, 2], "subtraces": 0},  # Func6 call
        ]

        # Validate trace structure and subtrace counts
        for i, expected in enumerate(expected_traces):
            result = tracer_response["result"][i]
            assert (
                result["traceAddress"] == expected["trace"]
            ), f"Trace {i} mismatch: expected {expected['trace']}, got {result['traceAddress']}"
            assert (
                result["subtraces"] == expected["subtraces"]
            ), f"Subtrace count mismatch for trace {i}: expected {expected['subtraces']}, got {result['subtraces']}"

    def test_transaction_return_data(self, transaction_return_data_receipt):
        receipt, expected_output = transaction_return_data_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        data_bytes = bytes.fromhex(tracer_response["result"][0]["result"]["output"][2:])
        decoded_output = default_codec.decode(["string"], data_bytes)[0]
        assert decoded_output == expected_output, "Expected output doesn't match with actual output"

    def test_transaction_in_chain_return_data_and_send_value(self, chain_with_return_data_receipt_and_contracts):
        receipt, expected_output = chain_with_return_data_receipt_and_contracts
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        assert len(tracer_response["result"]) == 2
        for i in range(len(tracer_response["result"])):
            data_bytes = bytes.fromhex(tracer_response["result"][i]["result"]["output"][2:])
            decoded_output = default_codec.decode(["string"], data_bytes)[0]
            assert decoded_output == expected_output, "Expected output doesn't match with actual output"

    def test_chain_of_transactions_reverted(self, chain_with_revert_receipt):
        receipt = chain_with_revert_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        error = decode_error_output(tracer_response["result"][2]["result"]["output"])
        expected_error_message = "Revert"
        assert expected_error_message in error

        assert len(tracer_response["result"]) == 3
        for i in range(len(tracer_response["result"])):
            resp = self.tracer_api.debug_trace_transaction(
                tracer_response["result"][i]["transactionHash"], tracer_type="callTracer", with_log=True
            )
            assert resp["result"]["calls"][0]["calls"][0]["error"] == "execution reverted"

    def test_chain_of_middle_transaction_reverted(self, chain_with_revert_in_middle_call_receipt_and_contracts):
        receipt, expected_output = chain_with_revert_in_middle_call_receipt_and_contracts
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        resp = self.tracer_api.debug_trace_transaction(
            tracer_response["result"][0]["transactionHash"], tracer_type="callTracer", with_log=True
        )
        assert resp["result"]["calls"][0]["calls"][1]["error"] == "execution reverted"

        data_bytes = bytes.fromhex(tracer_response["result"][2]["result"]["output"][2:])
        decoded_output = default_codec.decode(["string"], data_bytes)[0]
        assert decoded_output == expected_output, "Expected output doesn't match with actual output"

    def test_canceled_transaction(self, canceled_tx_with_hash_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(canceled_tx_with_hash_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(canceled_tx_with_hash_receipt["transactionHash"].hex())

        self.tracer_validator.check_trace_transaction_response(tracer_response, tx_data)

        assert tracer_response["result"][0]["action"]["callType"] == "stop"
        assert tx_data["from"].lower() == tracer_response["result"][0]["action"]["from"].lower()
        assert tx_data["to"].lower() == tracer_response["result"][0]["action"]["to"].lower()
        assert tx_data["input"].hex().lower() == tracer_response["result"][0]["action"]["input"].lower()[2:]
        assert tracer_response["result"][0]["action"]["gas"] == hex(tx_data["gas"])
