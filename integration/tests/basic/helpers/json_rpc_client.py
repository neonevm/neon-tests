import allure
import dataclasses
import requests
import typing as tp
from requests.models import Response

from integration.tests.basic.model.model import JsonRpcErrorResponse, JsonRpcResponse


class JsonRpcClient:
    """Implements simple JSON RPC client"""

    def __init__(self, proxy_url: str, session: requests.Session = None):
        self._url = proxy_url
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
