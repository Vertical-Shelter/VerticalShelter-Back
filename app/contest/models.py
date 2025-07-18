import datetime
import json
from typing import List, Optional

from fastapi import Depends, File, Form, UploadFile
from pydantic import BaseModel, model_validator

from ..User.models import UserResp


class MiniContestResp(BaseModel):
    title: str
    description: str
    image_url: str


class Bloc(BaseModel):
    zones: Optional[int]
    numero: int


class BlocResp(Bloc):
    id: str


class ListBloc(BaseModel):
    blocs: List[Bloc]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"blocs": new_value})
        return value


class Phase(BaseModel):
    numero: int
    startTime: str
    duree: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value["startTime"], datetime.datetime):
            value["startTime"] = value["startTime"].time().isoformat()[:8]
        elif isinstance(value["startTime"], datetime.time):
            value["startTime"] = value["startTime"].isoformat()[:8]

        if isinstance(value["duree"], datetime.timedelta):
            value["duree"] = str(value["duree"])

        return value


class PhaseResp(Phase):
    id: str


class ListPhase(BaseModel):
    phase: List[Phase]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"phase": new_value})
        return value


class IsBlocSucceed(BaseModel):
    isSucceed: bool
    isZoneSucceed: List[bool]
    blocId: str


class ListIsBlocSucceed(BaseModel):
    score: List[IsBlocSucceed]
    
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"score": new_value})
        return value


class State(enumerate):
    A_VENIR = -1
    EN_COURS = 0
    TERMINE = 1


class CreateContest(BaseModel):
    title: str
    description: str
    date: str
    priceE: int
    priceA: int
    blocs: List[Bloc]
    phases: List[Phase]
    hasFinal: bool
    doShowResults: Optional[bool] = True

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value["blocs"], str):
            new_value = json.loads(value["blocs"])
            value["blocs"] = new_value
        if isinstance(value["phases"], str):
            new_value = json.loads(value["phases"])
            value["phases"] = new_value
        return value
    
class CreateContestResp(CreateContest):
    id: str
    etat: int
    image_url: str
    blocs: List[BlocResp] = []
    qrCode_url: str
    phases: List[PhaseResp] = []
    rankingNames: List[str] = []


class InscriptionResp(BaseModel):
    id: str
    genre: str
    nom: str
    prenom: str
    points: Optional[int] = None
    blocs: Optional[List[IsBlocSucceed]] = []
    user: UserResp
    phaseId: PhaseResp = None
    isSubscribed: Optional[bool] = False
    qrCodeScanned: Optional[bool] = False


class ContestResp(BaseModel):
    id: str
    title: str
    description: str
    date: str
    priceE: int
    priceA: int
    etat: int
    image_url: str
    qrCode_url: str
    hasFinal: bool
    pointsPerZone: Optional[int] = 500
    isSubscribed: Optional[bool] = False
    qrCodeScanned: Optional[bool] = False

    blocs: List[BlocResp] = []
    phases: List[PhaseResp] = []
    inscriptionList: List[InscriptionResp] = []
    rankingNames: List[str] = ["M", "F", "J"]

    version: int = 1

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, dict) and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].isoformat()[:19]
        return value


class ContestInscription(BaseModel):
    isGuest: bool
    genre: str
    nom: str
    prenom: str
    isMember: bool
    phaseId: str
    is18YO: bool
    


class ContestInscriptionResp(ContestInscription):
    id: str

class InscriptionScoreResp(BaseModel):
    id: str
    genre: str
    nom: str
    prenom: str
    isMember: bool
    points: int
    is18YO: Optional[bool] = False
    phaseId: Optional[str] = None
    user: Optional[dict] = None
    qrCodeScanned: Optional[bool] = False
    blocs: Optional[List[IsBlocSucceed]] = []
    
class UserInscriptionScoreResp(InscriptionScoreResp):
    # set blocs to an empty list
    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        value["blocs"] = []
        return value