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
        self._session = session or requests.Session()

    def do_call(self, json_doc: tp.Any, model: tp.Any = None) -> tp.Union[JsonRpcResponse, JsonRpcErrorResponse]:
        """Implements light-weight remote procedure call (RPC) protocol."""
        if not isinstance(json_doc, tp.Dict):
            json_doc = dataclasses.asdict(json_doc)
        with allure.step(f"Request params: {json_doc}"):
            response = self._session.post(self._url, json=json_doc)
            return self._deserialize_response(response, model=model)

    @staticmethod
    def _deserialize_response(
        response: Response, model: tp.Any = None
    ) -> tp.Union[JsonRpcResponse, JsonRpcErrorResponse]:
        json_doc = response.json()
        with allure.step(f"Response data: {json_doc}"):
            if "error" in json_doc:
                response = JsonRpcErrorResponse(**json_doc)
            else:
                if model:
                    json_doc.update(dict(result=model.from_dict(json_doc["result"])))
                response = JsonRpcResponse(**json_doc)
        return response

    @property
    def is_devnet(self) -> bool:
        return "devnet" in self._url
