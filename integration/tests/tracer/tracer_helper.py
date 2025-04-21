import json
import pathlib

from jsonschema import Draft4Validator

SCHEMAS = "./integration/tests/tracer/schemas/"


def get_schema(file_name):
    with open(pathlib.Path(SCHEMAS, file_name)) as f:
        d = json.load(f)
        return d


def validate_response_result(response):
    schema = get_schema("debug_traceCall.json")
    validator = Draft4Validator(schema)
    assert validator.is_valid(response["result"])


def check_call_tracer_type(
    tracer_api,
    tx_data,
    wait_error=False,
    error_message="",
):
    params = ["0x" + tx_data["hash"].hex(), {"tracer": "callTracer", "tracerConfig": {"withLog": True}}]
    response = tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

    assert response["result"]["from"].lower() == tx_data["from"].lower()
    assert response["result"]["to"].lower() == tx_data["to"].lower()
    assert response["result"]["input"].lower() == "0x" + tx_data["input"].hex().lower()
    assert response["result"]["type"] == "CALL"

    if wait_error:
        assert "error" in response["result"]
        assert (
            response["result"]["error"] == error_message
        ), f'Waited {error_message}, got {response["result"]["error"]}'
    else:
        assert "error" not in response["result"]

    return response


def check_struct_log_type(
    tracer_api,
    tx_data,
    wait_error=False,
    wait_return_value=False,
    return_value="",
    check_struct_logs=True,
):
    params = [
        {
            "to": tx_data["to"],
            "from": tx_data["from"],
            "gas": hex(tx_data["gas"]),
            "gasPrice": hex(tx_data["gasPrice"]),
            "value": hex(tx_data["value"]),
            "data": "0x" + tx_data["input"].hex(),
        },
        hex(tx_data["blockNumber"]),
    ]

    response = tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

    if check_struct_logs:  # no structLogs in transactions from precompiled contracts
        assert len(response["result"]["structLogs"]) > 0, "No structLogs in response"

    if wait_error:
        assert response["result"]["failed"] is True
    else:
        assert response["result"]["failed"] is False, "Error in response"
    if wait_return_value:
        assert (
            response["result"]["returnValue"] == return_value
        ), f'Waited {return_value}, got {response["result"]["returnValue"]}'
    validate_response_result(response)

    return response
