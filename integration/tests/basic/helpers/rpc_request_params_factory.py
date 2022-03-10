import allure
from typing import List, Union

from integration.tests.basic.helpers.rpc_request_factory import ALLURE_PARAMS_BUILT
from integration.tests.basic.model.model import JsonRpcRequestParams
from integration.tests.basic.model.tags import Tag


class RpcRequestParamsFactory:
    @classmethod
    def get_block_by_number(
            cls, quantity_tag: Union[int, Tag],
            full_trx_object: bool) -> Union[List, JsonRpcRequestParams]:
        with allure.step(ALLURE_PARAMS_BUILT):
            q_tag = quantity_tag if isinstance(quantity_tag,
                                               int) else quantity_tag.value
            return [q_tag, full_trx_object]

    @classmethod
    def get_call(cls, quantity_tag: Union[int, Tag],
                 full_trx_object: bool) -> Union[List, JsonRpcRequestParams]:
        with allure.step(ALLURE_PARAMS_BUILT):
            # TODO: implement this
            return []

    @classmethod
    def get_logs(cls, quantity_tag: Union[int, Tag],
                 full_trx_object: bool) -> Union[List, JsonRpcRequestParams]:
        with allure.step(ALLURE_PARAMS_BUILT):
            # TODO: implement this
            return []