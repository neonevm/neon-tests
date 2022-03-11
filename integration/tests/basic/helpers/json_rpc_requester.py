import allure
import dataclasses
import requests
from requests.models import Response
from typing import Type, Union

from integration.tests.basic.model.model import JsonRpcErrorResponse, JsonRpcRequest, JsonRpcResponse


class JsonRpcRequester:
    def __init__(self, proxy_url: str):
        self._url = proxy_url
        self._session = requests.Session()

    @allure.step("requesting Json-RPC")
    def request_json_rpc(self, data: JsonRpcRequest) -> Response:
        with allure.step("getting response"):
            return self._session.post(self._url, json=dataclasses.asdict(data))

    # TODO: deserialize subobject
    @allure.step("deserializing response from JSON")
    def deserialize_response(
            self,
            response: Response,
            type: Type = None) -> Union[JsonRpcResponse, JsonRpcErrorResponse]:
        str_data = self.stringify(response.json())
        with allure.step("deserialized"):
            if 'result' in str_data:
                # return JsonRpcResponse(**response.json())
                return self.deserialize_successful_response(response=response,
                                                            type=type)
            elif 'error' in str_data:
                return JsonRpcErrorResponse(**response.json())
            else:
                return JsonRpcErrorResponse(**response.json())

    def deserialize_successful_response(self, response: Response,
                                        type: Type) -> JsonRpcResponse:
        json_rpc_response = JsonRpcResponse(**response.json())
        if type == None:
            return json_rpc_response
        subobject = type(**json_rpc_response.result)
        json_rpc_response.result = subobject
        return json_rpc_response

    @allure.step("showing as JSON")
    def stringify(self, data) -> str:
        return str(data)