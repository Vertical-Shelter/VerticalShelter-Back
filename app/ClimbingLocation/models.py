from pydantic import BaseModel, root_validator
from typing import List, Optional
from fastapi import Form, File, UploadFile
from ..settings import firestore_db
import datetime

from ..SprayWall.models import Annotation


class Grade(BaseModel):
    ref1: str
    ref2: Optional[str]
    vgrade: int

    def to_dict(self):
        return {
            "ref1": self.ref1,
            "ref2": self.ref2,
            "vgrade": self.vgrade,
        }
    
class GradeResp(Grade):
    id: str
    

def get_grades(climbingLocation_id):
    grades = (
        firestore_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("grades")
        .stream()
    )
    res = []
    for grade in grades:
        dict_grade = grade.to_dict()
        dict_grade["id"] = grade.id
        res.append(dict_grade)
    return res

class Secteur(BaseModel):
    newlabel: Optional[str] = None
    label: Optional[str] = None
    image: Optional[List[str]] = []
    qrCode: Optional[str] = None

    @root_validator(pre=True)
    def set_labels(cls, values):
        if values.get('newlabel'):
            values['label'] = values['newlabel']
        elif values.get('label'):
            values['newlabel'] = values['label']
        return values
    
class SecteurResp(Secteur):
    id: str


class WallSecteurResp(BaseModel):
    id: str
    newlabel: Optional[str] = None
    label: Optional[str] = None
    images: Optional[List[str]] = []
    annotations: Optional[List[Annotation]] = []

    @root_validator(pre=True)
    def set_labels(cls, values):
        if values.get('newlabel'):
            values['label'] = values['newlabel']
        elif values.get('label'):
            values['newlabel'] = values['label']

        if values.get('image') and not values.get('images'):
            values['images'] = values['image']
        return values

class ClimbingLocation(BaseModel):
    name: str
    address: str
    city: str
    country: str
    grades: List[Grade]
    secteurs: List[Secteur]
    description: Optional[str] = None
    image_url: Optional[str] = None
    topo_url: Optional[str] = None
    new_topo_url : Optional[str] = None
    ouvreurNames: Optional[List[str]] = None
    nextClosedSector: Optional[str | int] = None
    newNextClosedSector: Optional[str | int] = None
    isPartnership: Optional[bool] = False
    listNewLabel: Optional[List[str]] = []
    listNextSector : Optional[List[str | int]] = []
    attributes: Optional[List[str]] = []
    holds_color: Optional[List[str]] = []

class ClimbingLocationResp(ClimbingLocation):
    id: str
    grades: Optional[List[GradeResp]] = []
    secteurs: Optional[List[SecteurResp]] = []
    actual_contest: Optional["ContestResp"] | Optional["TeamContestResp"] = None

from ..contest.models import ContestResp
from ..TeamContest.models import TeamContestResp
