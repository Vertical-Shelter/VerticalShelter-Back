"""all the responses derived from the sentwall table will be defined here"""

import datetime
from pydantic import BaseModel, model_validator
from typing import Optional

"""
sentwall table: 
- id: str
- date: datetime
- wall_id: str
- user_id: str
- attributes: List[str]
- grade_id: str
- vgrade: str
- cloc_id: str
- secteur_id: str
- secteur_label: str
"""

### SentWalls

class SentWallRow(BaseModel):
    id: str
    date: str
    wall_id: str
    user_id: str
    attributes: list[str] = []
    grade_id: str
    vgrade: str
    cloc_id: str
    secteur_id: str
    secteur_label: str

class SentWallRowResp(BaseModel):
    id: Optional[str] = None
    date: Optional[str] = None
    wall_id: Optional[str] = None
    user_id: Optional[str] = None
    attributes: Optional[list[str]] = None
    grade_id: Optional[str] = None
    vgrade: Optional[int] = None
    cloc_id: Optional[str] = None
    secteur_id: Optional[str] = None
    secteur_label: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d %H:%M:%S")
        return value

class ClocStatsResp(BaseModel):
    id: str
    count_sentwalls: int = 0
    count_attributes: dict[str, int] = {}
    count_grades: dict[str, int] = {}
    sessions: dict[str, list[SentWallRowResp]] = {}


class WallStatsResp(SentWallRowResp):
    count_sentwalls: int = 0
    sentwalls: dict[str, int] = {}

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d")
        return value