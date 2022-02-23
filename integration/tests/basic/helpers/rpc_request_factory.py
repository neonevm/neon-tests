import allure
from typing import List, Union
from integration.tests.basic.model.json_rpc_methods import JsonRpcMethods
from integration.tests.basic.model.json_rpc_request import JsonRpcRequest
from integration.tests.basic.model.json_rpc_request_parameters import JsonRpcRequestParams

ALLURE_RETURN_VALUE_DESCRIPTION = "the model built"


class RpcRequestFactory:
    @classmethod
    def get_block_by_hash(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(
                id=req_id,
                method=JsonRpcMethods.GET_BLOCK_BY_HASH.value,
                params=params)

    @classmethod
    def get_block_by_number(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(
                id=req_id,
                method=JsonRpcMethods.GET_BLOCK_BY_NUMBER.value,
                params=params)

    @classmethod
    def get_block_number(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.BLOCK_NUMBER.value,
                                  params=params)

    @classmethod
    def get_call(cls, req_id: int,
                 params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.CALL.value,
                                  params=params)

    @classmethod
    def get_estimate_gas(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.ESTIMATE_GAS.value,
                                  params=params)

    @classmethod
    def get_gas_price(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GAS_PRICE.value,
                                  params=params)

    @classmethod
    def get_logs(cls, req_id: int,
                 params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_LOGS.value,
                                  params=params)

    @classmethod
    def get_balance(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_BALANCE.value,
                                  params=params)

    @classmethod
    def get_trx_count(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_TRX_COUNT.value,
                                  params=params)

    @classmethod
    def get_code(cls, req_id: int,
                 params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_CODE.value,
                                  params=params)

    @classmethod
    def get_send_raw_trx(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.SEND_RAW_TRX.value,
                                  params=params)

    @classmethod
    def get_trx_by_hash(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_TRX_BY_HASH.value,
                                  params=params)

    @classmethod
    def get_trx_receipt(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_TRX_RECEIPT.value,
                                  params=params)

    @classmethod
    def get_storage_at(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.GET_STORAGE_AT.value,
                                  params=params)

    @classmethod
    def get_web3_client_version(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(
                id=req_id,
                method=JsonRpcMethods.WEB3_CLIENT_VERSION.value,
                params=params)

    @classmethod
    def get_net_version(
            cls, req_id: int,
            params: Union[List, JsonRpcRequestParams]) -> JsonRpcRequest:
        with allure.step(ALLURE_RETURN_VALUE_DESCRIPTION):
            return JsonRpcRequest(id=req_id,
                                  method=JsonRpcMethods.NET_VERSION.value,
                                  params=params)
