import datetime
import json
from typing import List, Optional

from pydantic import BaseModel, model_validator

### Roles

class ListRole(BaseModel):
    roles: List[str]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"roles": new_value})
        return value


### Blocs


class Bloc(BaseModel):
    numero: int
    points: Optional[int] = None
    zones: Optional[int] = 0
    multiplicator: Optional[List[int | float]] = []


class ListBloc(BaseModel):
    blocs: List[Bloc]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"blocs": new_value})
        return value
    
    @model_validator(mode="after")
    @classmethod
    def sort_blocs(cls, value):
        value.blocs = sorted(value.blocs, key=lambda x: x.numero)
        return value
    

class BlocResp(Bloc):
    image_url: Optional[str] = ""


### Phases


class Phase(BaseModel):
    numero: int
    startTime: str
    duree: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value["startTime"], datetime.datetime):
            value["startTime"] = value["startTime"].strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value["startTime"], datetime.time):
            value["startTime"] = value["startTime"].strftime("%H:%M:%S")

        if isinstance(value["duree"], datetime.timedelta):
            value["duree"] = str(value["duree"])

        return value


class ListPhase(BaseModel):
    phase: List[Phase]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"phase": new_value})
        return value


### Scoring


class ListScoring(BaseModel):
    """List scoring (int encoded list)"""
    score: List[int]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"score": new_value})
        return value


### Contest


class TeamContestBase(BaseModel):
    title: str
    description: str
    image_url: str

    date: str
    priceE: int
    priceA: int
    etat: int

    hasFinal: bool
    doShowResults: bool
    scoringType: str
    pointsPerZone: Optional[int] = 500

    roles: List[str] = []
    blocs: List[BlocResp] = []
    phases: List[Phase] = []
    rankingNames: List[str] = []


class TeamContestResp(TeamContestBase):
    id: str

    qrCode_url: str = ""
    isSubscribed: Optional[bool] = False
    version: int = 2

    @model_validator(mode="before")
    @classmethod
    def validate_date(cls, value):
        if isinstance(value, list) :
            for i in range(len(value)):
                value[i] = cls.model_validate(value[i])
        elif isinstance(value["date"], datetime.date) or isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].strftime("%Y-%m-%d")
        return value

class State(enumerate):
    A_VENIR = -1
    EN_COURS = 0
    TERMINE = 1

