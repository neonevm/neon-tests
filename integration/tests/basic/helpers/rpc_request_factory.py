from integration.tests.basic.model.json_rpc_methods import GET_BLOCK_BY_HASH, \
    GET_BLOCK_BY_NUMBER, BLOCK_NUMBER, CALL, ESTIMATE_GAS, GAS_PRICE, GET_LOGS, \
    GET_BALANCE, GET_TRX_COUNT, GET_CODE, SEND_RAW_TRX, GET_TRX_BY_HASH, \
    GET_TRX_RECEIPT, GET_STORAGE_AT, WEB3_CLIENT_VERSION, NET_VERSION
from integration.tests.basic.model.rpc_request import RpcRequest
from integration.tests.basic.model.rpc_request_parameters import RpcRequestParams


class RpcRequestFactory():
    def get_block_by_hash(self, id: int,
                          params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_BLOCK_BY_HASH, params=params)

    def get_block_by_number(self, id: int,
                            params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_BLOCK_BY_NUMBER, params=params)

    def get_block_umber(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=BLOCK_NUMBER, params=params)

    def get_call(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=CALL, params=params)

    def get_estimate_gas(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=ESTIMATE_GAS, params=params)

    def get_gas_price(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GAS_PRICE, params=params)

    def get_logs(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_LOGS, params=params)

    def get_balance(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_BALANCE, params=params)

    def get_trx_count(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_TRX_COUNT, params=params)

    def get_code(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_CODE, params=params)

    def get_send_raw_trx(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=SEND_RAW_TRX, params=params)

    def get_trx_by_hash(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_TRX_BY_HASH, params=params)

    def get_trx_receipt(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_TRX_RECEIPT, params=params)

    def get_storage_at(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=GET_STORAGE_AT, params=params)

    def get_web3_client_version(self, id: int,
                                params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=WEB3_CLIENT_VERSION, params=params)

    def get_net_version(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=NET_VERSION, params=params)
