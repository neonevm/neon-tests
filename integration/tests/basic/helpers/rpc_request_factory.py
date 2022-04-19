import random
import typing as tp

from integration.tests.basic.model.model import JsonRpcRequest, JsonRpcRequestParams


class RpcRequestFactory:

    GET_BLOCK_BY_HASH = "eth_getBlockByHash"
    GET_BLOCK_BY_NUMBER = "eth_getBlockByNumber"
    BLOCK_NUMBER = "eth_blockNumber"
    CALL = "eth_call"
    ESTIMATE_GAS = "eth_estimateGas"
    GAS_PRICE = "eth_gasPrice"
    GET_LOGS = "eth_getLogs"
    GET_BALANCE = "eth_getBalance"
    GET_TRX_COUNT = "eth_getTransactionCount"
    GET_CODE = "eth_getCode"
    SEND_RAW_TRX = "eth_sendRawTransaction"
    GET_TRX_BY_HASH = "eth_getTransactionByHash"
    GET_TRX_RECEIPT = "eth_getTransactionReceipt"
    GET_STORAGE_AT = "eth_getStorageAt"
    WEB3_CLIENT_VERSION = "web3_clientVersion"
    NET_VERSION = "net_version"

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
    def get_block_by_hash(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_BLOCK_BY_HASH, params=params)

    @classmethod
    def get_block_by_number(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_BLOCK_BY_NUMBER, params=params)

    @classmethod
    def get_block_number(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.BLOCK_NUMBER, params=params)

    @classmethod
    def get_call(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.CALL, params=params)

    @classmethod
    def get_estimate_gas(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.ESTIMATE_GAS, params=params)

    @classmethod
    def get_gas_price(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GAS_PRICE, params=params)

    @classmethod
    def get_logs(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_LOGS, params=params)

    @classmethod
    def get_balance(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_BALANCE, params=params)

    @classmethod
    def get_trx_count(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_TRX_COUNT, params=params)

    @classmethod
    def get_code(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_CODE, params=params)

    @classmethod
    def get_send_raw_trx(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.SEND_RAW_TRX, params=params)

    @classmethod
    def get_trx_by_hash(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_TRX_BY_HASH, params=params)

    @classmethod
    def get_trx_receipt(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_TRX_RECEIPT, params=params)

    @classmethod
    def get_storage_at(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.GET_STORAGE_AT, params=params)

    @classmethod
    def get_web3_client_version(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.WEB3_CLIENT_VERSION, params=params)

    @classmethod
    def get_net_version(cls, params: tp.Union[tp.List, JsonRpcRequestParams]) -> JsonRpcRequest:
        return JsonRpcRequest(id=cls.get_random_value(), method=cls.NET_VERSION, params=params)
