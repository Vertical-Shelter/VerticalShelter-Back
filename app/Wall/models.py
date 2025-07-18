from pydantic import BaseModel, model_validator
from typing import List, Optional
import datetime
import json


from ..User.models import UserResp, UserIdResp
from ..ClimbingLocation.models import WallSecteurResp, GradeResp, ClimbingLocationResp
from ..SprayWall.models import SprayWallHold


class LikeResp(BaseModel):
    id: str
    date: str
    user: UserResp

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d %H:%M:%S")
        return value


class CommentResp(BaseModel):
    id: str
    date: str
    user: UserResp
    comment: str

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d %H:%M:%S")
        return value


class WallParam(BaseModel):
    grade_id: str
    attributes: List[str]
    vsl_attributes: Optional[List[str]] = []
    wall_id: Optional[str] = None
    description: Optional[str] = None
    hold_to_take: Optional[str] = ""
    routesettername: Optional[str] = None
    date: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

    def to_dict(self):
        return {
            "grade_id": self.grade_id,
            "description": self.description,
            "hold_to_take": self.hold_to_take,
            "routesettername": self.routesettername,
            "attributes": self.attributes,
            "vsl_attributes": self.vsl_attributes,
            "date": self.date,
        }


class SentWallParam(BaseModel):
    id: str
    nTentative: int
    grade_id: Optional[str] = None
    grade_font : Optional[str] = None

class SentWallResp(BaseModel):
    id: str
    date: str
    user: Optional[UserResp] = None
    grade: Optional[GradeResp] = None
    wall: Optional["WallResp"] = None
    beta: Optional[str] = None
    nTentative: int
    grade_font : Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d %H:%M:%S")

        if "grade" in value and not isinstance(value.get("grade"), dict):
            value.pop("grade")

        if "wall" in value and not isinstance(value.get("wall"), dict):
            value["wall"] = None

        return value

class ListSentWall(BaseModel):
    sentwalls: List[SentWallParam]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"sentwalls": new_value})
        return value


class WallResp(BaseModel):
    id: str
    grade_id: str = ""
    grade: GradeResp = None
    secteur: WallSecteurResp = None
    climbingLocation: Optional[ClimbingLocationResp] = None

    date: Optional[str] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description: Optional[str] = ""
    name : Optional[str] = ""
    hold_to_take: Optional[str] = ""
    routesettername: Optional[str] = "" 
    routesetter: Optional[UserResp] = None
    attributes: List[str] = []
    vsl_attributes: Optional[List[str]] = []
    sentWalls: Optional[List[SentWallResp | UserIdResp]] = []
    betaOuvreur: Optional[str] = None
    nbRepetitions: Optional[int] = 0

    isDone: Optional[bool] = False
    isActual: Optional[bool] = False
    points: Optional[int] = None

    likes: Optional[List[LikeResp]] = []
    comments: Optional[List[CommentResp]] = []

    # spraywall specific
    holds: Optional[List[SprayWallHold]] = []
    equivalentExte: Optional[str] = None
    equivalentExteMean : Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d %H:%M:%S")

        if "sentWalls" in value:
            sentwalls = []
            for sentwall in value["sentWalls"]:
                # handle properly the case where the sentwall is a UserMiniResp
                if not isinstance(sentwall, dict):
                    sentwalls.append(UserIdResp(**{"id": sentwall.id}))
                elif "user" in sentwall:
                    sentwalls.append(SentWallResp(**sentwall))
                else:
                    sentwalls.append(UserIdResp(**sentwall))
                    
            value["nbRepetitions"] = len(sentwalls)
            value["sentWalls"] = sentwalls

        if "grade" in value:
            if not isinstance(value.get("grade"), dict) and value.get("grade") is not None:
                value["grade_id"] = value["grade"].id
                value["grade"] = None

        if "secteur" in value and not isinstance(value.get("secteur"), dict):
            value["secteur"] = None

        if "climbingLocation" in value and not isinstance(value.get("climbingLocation"), dict):
            value["climbingLocation"] = None

        if "routesetter" in value and not isinstance(value.get("routesetter"), dict):
            value["routesetter"] = None

        if "routesettername" in value and not isinstance(value["routesettername"], str):
            value["routesettername"] = ""

        if "hold_to_take" in value and not isinstance(value["hold_to_take"], str):
            value["hold_to_take"] = ""

        if "likes" in value:
            likes = []
            for like in value["likes"]:
                if not isinstance(like, dict):
                    likes.append({"id": like.id})
                else:
                    likes.append(like)
            value["likes"] = likes

        if "comments" in value:
            comments = []
            for comment in value["comments"]:
                if not isinstance(comment, dict):
                    comments.append({"id": comment.id})
                else:
                    if not 'comment' in comment:
                        comment['comment'] = ""
                    comments.append(comment)
            value["comments"] = comments

        if "points" in value and not isinstance(value["points"], int):
            try :
                value["points"] = int(value["points"])
            except:
                value["points"] = None

        #TODO: equivalentExte and equivalentExteMean

        return value


class WallOuvreurResp(WallResp):
    # just the id of the user instead of the full user object
    sentWalls: List[UserIdResp] = []


class Project(BaseModel):
    wall_id: str
    secteur_id: str
    climbingLocation_id: str
    is_spraywall: Optional[bool] = False

    def to_dict(self):
        return {
            "wall_id": self.wall_id,
            "sector_id": self.secteur_id,
            "climbingLocation_id": self.climbingLocation_id,
            "is_spraywall": self.is_spraywall,
        }


class ProjectResp(Project):
    wall_id: WallResp
    id: str

