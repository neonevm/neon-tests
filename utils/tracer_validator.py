import json
import pathlib

import allure
from jsonschema import Draft4Validator

from utils.models.result import TraceTransactionResponse

SCHEMAS = "./integration/tests/tracer/schemas/"


def get_schema(file_name):
    with open(pathlib.Path(SCHEMAS, file_name)) as f:
        d = json.load(f)
        return d


@allure.step("Validate debug_traceCall response by json scheme ")
def validate_response_result(response):
    schema = get_schema("debug_traceCall.json")
    validator = Draft4Validator(schema)
    assert validator.is_valid(response["result"])


class TracerValidator:

    @staticmethod
    @allure.step("check struct_log response")
    def check_tracer_struct_log(
        tracer_response, wait_result=True, wait_error=False, return_value: str = "", validation: bool = True
    ):
        if wait_error:
            assert tracer_response["result"]["failed"] is True
        else:
            assert "error" not in tracer_response["result"], "Error in tracer_response"
        if return_value:
            assert (
                tracer_response["result"]["returnValue"] == return_value
            ), f'Waited {return_value}, got {tracer_response["result"]["returnValue"]}'
        if wait_result:
            assert "result" in tracer_response
        if validation:
            validate_response_result(tracer_response)
        return True

    @staticmethod
    @allure.step("check callTracer response ")
    def check_call_tracer_type(
        tracer_response: dict,
        tx_data,
        error_message="",
    ) -> bool:

        assert tracer_response["result"]["from"].lower() == tx_data["from"].lower()
        assert tracer_response["result"]["to"].lower() == tx_data["to"].lower()
        assert tracer_response["result"]["input"].lower() == "0x" + tx_data["input"].hex().lower()
        assert tracer_response["result"]["type"] == "CALL"

        if error_message:
            assert "error" in tracer_response["result"]
            assert tracer_response["result"]["error"] == error_message
        else:
            assert "error" not in tracer_response["result"]
        return True

    @staticmethod
    @allure.step("check Trace_transaction response")
    def check_trace_transaction_response(
        tracer_response: dict,
        tx_data,
        tx_receipt=None,
        wait_error=False,
    ) -> bool:

        TraceTransactionResponse(**tracer_response)
        """check trace_transaction method response"""
        if wait_error:
            assert "error" in tracer_response, f"No Error in tracer_response: {tracer_response}"
        else:
            assert "error" not in tracer_response, f"Error in tracer_response: {tracer_response}"

        assert tx_data["from"].lower() == tracer_response["result"][0]["action"]["from"].lower()
        assert tx_data["to"].lower() == tracer_response["result"][0]["action"]["to"].lower()
        assert tx_data["hash"].to_0x_hex() == tracer_response["result"][0]["transactionHash"]
        assert tx_data["input"].to_0x_hex() == tracer_response["result"][0]["action"]["input"]
        assert tx_data["gas"] == int(tracer_response["result"][0]["action"]["gas"], 16)
        assert tracer_response["result"][0]["action"]["value"] == hex(tx_data["value"])

        if tx_receipt:
            assert tx_receipt["gasUsed"] == int(tracer_response["result"][0]["result"]["gasUsed"], 16)

        assert len(tracer_response["result"]) > 0, f"tracer_response: {tracer_response}"
        for i in range(len(tracer_response["result"])):
            assert tx_data["blockHash"].to_0x_hex() == tracer_response["result"][i]["blockHash"]
            assert tx_data["blockNumber"] == tracer_response["result"][i]["blockNumber"]
