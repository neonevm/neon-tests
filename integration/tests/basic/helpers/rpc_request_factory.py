import random
import typing as tp

from integration.tests.basic.model.model import JsonRpcRequest, JsonRpcRequestParams


class RpcRequestFactory:

    SEND_RAW_TRX = "eth_sendRawTransaction"

    def __getattr__(self, eth_method) -> tp.Callable:
        """RPC request constructor"""

        def wrapper(*args, **kwargs):
            params = list(filter(None, args))
            params.extend(kwargs.values())
            return JsonRpcRequest(id=self.get_random_value(), method=eth_method, params=params)

        return wrapper

    @classmethod
    def get_random_value(cls) -> int:
        return random.randint(0, 100)

    @classmethod
    def build_send_raw_trx(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.SEND_RAW_TRX, params=params)
