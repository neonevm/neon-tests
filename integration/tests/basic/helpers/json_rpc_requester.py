import allure
import dataclasses
import requests
from requests.models import Response
from typing import Union
from integration.tests.basic.model.json_rpc_error_response import JsonRpcErrorResponse

from integration.tests.basic.model.json_rpc_request import JsonRpcRequest
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse


class JsonRpcRequester:
    def __init__(self, proxy_url: str):
        self._url = proxy_url
        self._session = requests.Session()

    @allure.step("requesting Json-RPC")
    def request_json_rpc(self, data: JsonRpcRequest) -> Response:
        with allure.step("getting response"):
            return self._session.post(self._url, json=dataclasses.asdict(data))

    @allure.step("deserializing response from JSON")
    def deserialize_response(
            self, response: Response
    ) -> Union[JsonRpcResponse, JsonRpcErrorResponse]:
        str_data = self.stringify(response.json())
        with allure.step("deserialized"):
            if 'result' in str_data:
                return JsonRpcResponse(**response.json())
            elif 'error' in str_data:
                return JsonRpcErrorResponse(**response.json())
            else:
                return JsonRpcErrorResponse(**response.json())

    @allure.step("showing as JSON")
    def stringify(self, data) -> str:
        return str(data)