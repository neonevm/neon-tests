import allure
import dataclasses
import requests
from requests.models import Response

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

    @allure.step("deserializing from JSON")
    def deserialize(self, data: str) -> JsonRpcResponse:
        with allure.step("deserialized"):
            return JsonRpcResponse(**data)
