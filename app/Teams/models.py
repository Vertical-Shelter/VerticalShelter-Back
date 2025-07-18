import datetime
import json
from typing import Dict, List, Optional

from pydantic import BaseModel, model_validator

from ..User.models import UserTeamResp
from ..VSL.models import HistoryResp


class InscriptionParam(BaseModel):
    first_name: str
    last_name: str
    gender: str
    age: int
    # should we make those optional?
    address: Optional[str] = None
    city: str
    postal_code: str
    role: Optional[str] = None
    t_shirt_size: Optional[str] = None
    is_guest: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**new_value)
        return value


class TeamBase(BaseModel):
    climbingLocation_id: str

    name: str
    description: Optional[str] = ""
    image_url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            value = json.loads(value)
        return value


class ContestTeamBase(TeamBase):
    phase: int


class TeamResp(TeamBase):
    id: str
    event_id: str
    is_owner: bool = False
    members: List[UserTeamResp] = []  # inside db it's a dict of user_id: user_ref
    roles: Dict[str, str] = {}  # role: user_id ; easily map role to user_id

    access_code: Optional[str] = ""
    points: int = 0

    # contest specific
    phase: Optional[int] = None

    # vsl specific
    history: List["HistoryResp"] = None

    @model_validator(mode="before")
    @classmethod
    def members_dict_to_list(cls, value):
        if "members" in value and isinstance(value["members"], dict):
            value["members"] = list(value["members"].values())
        if "points" in value and isinstance(value["points"], float):
            value["points"] = int(value["points"])
        return value
