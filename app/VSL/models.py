import datetime
import json

from pydantic import BaseModel, model_validator
from typing import List, Optional

from ..Wall.models import SentWallResp


ROLES = ["ninja", "gecko", "gorille"]

### VSL

class VSLBase(BaseModel):
    title: str
    description: Optional[str] = ""
    inscription_start_date: datetime.datetime
    start_date: datetime.datetime
    end_date: datetime.datetime
    image_url: Optional[str] = ""
    is_actual: bool = True
    roles: List[str] = ROLES

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            value = json.loads(value)

        if "inscription_start_date" not in value:
            value["inscription_start_date"] = value["start_date"]

        return value


class VSLResp(VSLBase):
    id: str


### League

class LeagueBase(BaseModel):
    vsl_id: str
    climbingLocation_id: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**new_value)
        return value


class LeagueResp(LeagueBase):
    id: str

    # climbingLocation stuff
    name: str
    city: str
    image_url: Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def cloc_id_to_id(cls, value):
        if "climbingLocation_id" in value:
            value["id"] = value["climbingLocation_id"]

        return value


### History

class HistoryResp(BaseModel):
    sentWall: SentWallResp
    points: int
    raw_points: int
    user_id: str
    user_role: str
    date: datetime.datetime
    vsl_attributes: List[str] # ["gorille"] # contains the role