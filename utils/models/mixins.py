from pydantic import BaseModel, ConfigDict


class ForbidExtra(BaseModel):
    model_config = ConfigDict(extra="forbid")
