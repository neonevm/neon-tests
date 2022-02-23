from integration.tests.basic.model.json_rpc_methods import JsonRpcMethods
from integration.tests.basic.model.rpc_request import RpcRequest
from integration.tests.basic.model.rpc_request_parameters import RpcRequestParams


class RpcRequestFactory():
    def get_block_by_hash(self, id: int,
                          params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_BLOCK_BY_HASH,
                          params=params)

    def get_block_by_number(self, id: int,
                            params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_BLOCK_BY_NUMBER,
                          params=params)

    def get_block_umber(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.BLOCK_NUMBER,
                          params=params)

    def get_call(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=JsonRpcMethods.CALL, params=params)

    def get_estimate_gas(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.ESTIMATE_GAS,
                          params=params)

    def get_gas_price(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GAS_PRICE,
                          params=params)

    def get_logs(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=JsonRpcMethods.GET_LOGS, params=params)

    def get_balance(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_BALANCE,
                          params=params)

    def get_trx_count(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_TRX_COUNT,
                          params=params)

    def get_code(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method=JsonRpcMethods.GET_CODE, params=params)

    def get_send_raw_trx(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.SEND_RAW_TRX,
                          params=params)

    def get_trx_by_hash(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_TRX_BY_HASH,
                          params=params)

    def get_trx_receipt(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_TRX_RECEIPT,
                          params=params)

    def get_storage_at(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.GET_STORAGE_AT,
                          params=params)

    def get_web3_client_version(self, id: int,
                                params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.WEB3_CLIENT_VERSION,
                          params=params)

    def get_net_version(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id,
                          method=JsonRpcMethods.NET_VERSION,
                          params=params)
