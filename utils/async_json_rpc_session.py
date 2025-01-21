import asyncio
import typing as tp

import httpx


class JsonRpcRequest(tp.TypedDict):
    method: str
    params: tp.Optional[tp.Union[dict[str, tp.Any], list[tp.Any]]]


class AsyncJsonRpcSession(httpx.AsyncClient):
    def __init__(self, url: str, **kwargs):
        super().__init__(base_url=url, **kwargs)

    async def request_rpc(
        self,
        method: str,
        params: tp.Any = None,
        id_: int = 1,
        semaphore: asyncio.Semaphore = asyncio.Semaphore(100),
    ) -> httpx.Response:
        json_rpc_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": id_,
        }
        async with semaphore:
            response = await self.post(self.base_url, json=json_rpc_payload)

        return response

    async def batch_request_rpc(
        self,
        requests: list[JsonRpcRequest],
        semaphore: asyncio.Semaphore = asyncio.Semaphore(100),
    ) -> httpx.Response:
        json_rpc_payloads = [
            {
                "jsonrpc": "2.0",
                "method": req["method"],
                "params": req.get("params", {}),
                "id": idx + 1,
            }
            for idx, req in enumerate(requests)
        ]
        async with semaphore:
            response = await self.post("", json=json_rpc_payloads)
        return response
