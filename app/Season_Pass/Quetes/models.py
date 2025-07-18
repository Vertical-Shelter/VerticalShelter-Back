from pydantic import BaseModel, model_validator
from datetime import datetime

QUETE_TYPE = ["Q1", "Q2", "Q3", "Q4", "QP1", "QP2", "QH1", "QH2"]


class Quete(BaseModel):
    title: str
    description: str
    image_url: str
    xp: int
    quota: int
    type: str


class QueteReturn(Quete):
    # read_only
    id: str


class UserQuete(BaseModel):
    queteId: QueteReturn
    id: str
    quota: int
    date: datetime
    is_claimed: bool
    is_claimable: bool
