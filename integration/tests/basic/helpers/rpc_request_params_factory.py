import typing as tp
from integration.tests.basic.model.model import JsonRpcRequestParams
from integration.tests.basic.model.tags import Tag


class RpcRequestParamsFactory:
    @classmethod
    def get_block_by_number(
        cls, quantity_tag: tp.Union[int, Tag], full_trx_object: bool
    ) -> tp.Union[tp.List, JsonRpcRequestParams]:
        q_tag = quantity_tag if isinstance(quantity_tag, int) else quantity_tag.value
        return [q_tag, full_trx_object]
