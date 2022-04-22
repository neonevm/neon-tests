import dataclasses
import typing as tp

import allure
import requests
from requests.models import Response

from integration.tests.basic.model.model import JsonRpcErrorResponse, JsonRpcResponse


class JsonRpcClient:
    """Implements simple JSON RPC client"""

    def __init__(self, proxy_url: str, session: requests.Session = None):
        self._url = proxy_url
# <<<<<<< HEAD
#         self._session = requests.Session()

#     def request_json_rpc(self, data: JsonRpcRequest) -> Response:
#         with allure.step(f"Request: {data}"):
#             return self._session.post(self._url, json=dataclasses.asdict(data))

#     def deserialize_response(
#         self, response: Response, type: Type = None
#     ) -> Union[JsonRpcResponse, JsonRpcErrorResponse]:
#         str_data = str(response.json())
#         with allure.step(f"Response: {str_data}"):
#             if "result" in str_data:
#                 return self.deserialize_successful_response(response=response, type=type)
#             elif "error" in str_data:
#                 return JsonRpcErrorResponse(**response.json())
#             else:
#                 return JsonRpcErrorResponse(**response.json())

#     def deserialize_successful_response(self, response: Response, type: Type) -> JsonRpcResponse:
#         json_rpc_response = JsonRpcResponse(**response.json())
#         if type == None:
#             return json_rpc_response

#         result_dict = dict(json_rpc_response.result)
#         result_subobject = type.from_dict(result_dict)
#         json_rpc_response.result = result_subobject
#         return json_rpc_response
# =======
        self._session = session or requests.Session()

    def do_call(self, payloads: tp.Any, model: tp.Any = None) -> tp.Union[JsonRpcResponse, JsonRpcErrorResponse]:
        """Implements light-weight remote procedure call (RPC) protocol."""
        if not isinstance(payloads, tp.Dict):
            payloads = dataclasses.asdict(payloads)
        with allure.step(f"Request params: {payloads}"):
            response = self._session.post(self._url, json=payloads)
            return self._deserialize_response(response, model=model)

    @staticmethod
    def _deserialize_response(
        response: Response, model: tp.Any = None
    ) -> tp.Union[JsonRpcResponse, JsonRpcErrorResponse]:
        try:
            json_doc = response.json()
        except requests.exceptions.JSONDecodeError:
            return JsonRpcErrorResponse()
        with allure.step(f"Response data: {json_doc}"):
            if "error" in json_doc:
                response = JsonRpcErrorResponse(**json_doc)
            else:
                if model:
                    json_doc.update(dict(result=model.from_dict(json_doc["result"])))
                response = JsonRpcResponse(**json_doc)
        return response

# >>>>>>> develop
