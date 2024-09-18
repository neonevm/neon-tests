import pydantic

from utils.models.model_types import HexString


class CostReportAction(pydantic.BaseModel):
    name: str
    usedGas: int
    gasPrice: int
    tx: HexString


class CostReportModel(pydantic.BaseModel):
    name: str
    actions: list[CostReportAction] = []
