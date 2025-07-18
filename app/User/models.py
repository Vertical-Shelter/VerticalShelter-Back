from pydantic import BaseModel, model_validator
from typing import List, Dict, Optional
from ..gameDesign.gameObject import AvatarReturn, BaniereReturn


class UserPatchResp(BaseModel):
    id: str
    email: Optional[str] = None
    username: str
    isGym: Optional[bool] = False
    isAmbassadeur: Optional[bool] = False
    profile_image_url: Optional[str] = ""
    climbingLocation: Optional["ClimbingLocationResp"] | dict | None = None
    climbingLocation_id: Optional[str] = None
    description: Optional[str] = ""
    avatar: Optional[AvatarReturn] = None
    baniere: Optional[AvatarReturn] = None


class UserIdResp(BaseModel):
    id: str


class UserResp(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    profile_image_url: Optional[str | None] = None
    isSubscribed: Optional[bool] = False
    climbinbingLocation_id: Optional["ClimbingLocationResp"] = None
    subscribed_topics: Optional[Dict[str, bool]] = {}


class UserRespExtended(UserResp):
    friendStatus: Optional[str] = "NOT_FRIEND"
    sentWalls: Optional[List["SentWallResp"]] = []  # forward reference


class UserVSLResp(BaseModel):
    id: str
    username: Optional[str] = None
    points: Optional[float] = 0
    profile_image_url: Optional[str] = None
    gender: Optional[str] = None


class UserMinimalResp(BaseModel):
    id: str
    username: str
    profile_image_url: Optional[str] = None


class UserRankingResp(UserMinimalResp):
    points: float = 0


class UserTeamResp(UserMinimalResp):
    blocs: Optional[list[int]] = None
    gender : Optional[str] = None
    points: Optional[int] = 0
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    isSubscribed: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if "points" in value and isinstance(value["points"], float):
            value["points"] = int(value["points"])
        return value



class VideoResp(BaseModel):
    url: str


# avoid circular import
from ..Wall.models import SentWallResp
from ..ClimbingLocation.models import ClimbingLocationResp