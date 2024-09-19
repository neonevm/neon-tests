import typing as tp

from utils.models.mixins import ForbidExtra
from utils.models.model_types import HexString


class EthFeeHistoryResult(ForbidExtra):
    baseFeePerGas: list[HexString]
    gasUsedRatio: list[tp.Union[int, float]]
    oldestBlock: HexString
    reward: tp.Optional[list[list[HexString]]] = None
