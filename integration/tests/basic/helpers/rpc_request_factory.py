from integration.tests.basic.model.rpc_request import RpcRequest
from integration.tests.basic.model.rpc_request_parameters import RpcRequestParams


class RpcRequestFactory():
    def get_block_by_hash(self, id: int,
                          params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_block_by_number(self, id: int,
                            params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_block_umber(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_call(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_estimate_gas(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_gas_price(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_logs(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_balance(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_trx_count(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_code(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_send_raw_trx(self, id: int,
                         params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_trx_by_hash(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_trx_receipt(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_storage_at(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_web3_client_version(self, id: int,
                                params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)

    def get_net_version(self, id: int, params: RpcRequestParams) -> RpcRequest:
        return RpcRequest(id=id, method="", params=params)