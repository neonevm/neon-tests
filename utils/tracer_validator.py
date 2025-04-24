from integration.tests.tracer.tracer_helper import validate_response_result
from utils.tracer_client import TracerClient


class TracerValidator(TracerClient):
    def __init__(self, web3_client, url):
        super().__init__(url)
        self.web3_client = web3_client

    def _get_tx_data(self, tx_receipt):
        """Get transaction data by receipt."""
        return self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"].hex())

    def check_tracer_struct_log(
        self, tx_data, wait_error=False, error_message="", wait_return_value=False, return_value=""
    ):

        response = self.debug_trace_call(tx_data)

        if wait_error:
            assert response["result"]["failed"] is True
        else:
            assert "error" not in response["result"], "Error in response"
        if wait_return_value:
            assert (
                response["result"]["returnValue"] == return_value
            ), f'Waited {return_value}, got {response["result"]["returnValue"]}'
        validate_response_result(response)

    def check_call_tracer_type(
        self,
        tx_data,
        wait_error=False,
        error_message="",
    ):

        response = self.debug_trace_transaction(
            "debug_traceTransaction", tracer_type="callTracer", wait_response=120, with_log=True
        )

        assert response["result"]["from"].lower() == tx_data["from"].lower()
        assert response["result"]["to"].lower() == tx_data["to"].lower()
        assert response["result"]["input"].lower() == "0x" + tx_data["input"].hex().lower()
        assert response["result"]["type"] == "CALL"

        if wait_error:
            assert "error" in response["result"]
            assert response["result"]["error"] == error_message
        else:
            assert "error" not in response["result"]

    def check_all_tracer_types(self, receipt):
        """Check that all trace types work correctly with tx"""
        tx_data = self._get_tx_data(receipt)
        self.check_tracer_struct_log(tx_data)
        self.check_call_tracer_type(tx_data)
