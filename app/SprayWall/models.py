from pydantic import BaseModel, model_validator
from typing import List, Optional
from fastapi import Form, File, UploadFile
import datetime
import json

from ..settings import firestore_db

style = [
    "No foot",
    "pince",
    "plat",
    "reglette",
    "compression",
    "dynamisme"
]

class Annotation(BaseModel):
    """COCO format"""
    id: str
    category_id: int # id of the category
    segmentation: List[float] # [x1, y1, x2, y2, ...]
    bbox: Optional[List[float]] = [] # [x1, y1, x2, y2]
    area: Optional[float] = 0.0
    iscrowd: Optional[int] = 0

class Annotations(BaseModel):
    annotations: List[Annotation]

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            new_value = json.loads(value)
            return cls(**{"annotations": new_value})
        return value

class SprayWallResp(BaseModel):
    id: str
    climbingLocation_id: Optional[str] = ""
    image: Optional[str] = ""
    annotations: Optional[List[Annotation]] = []
    label: Optional[str] = ""

class SprayWallHold(BaseModel):
    id: str # id of the annotation
    type: int # eg: 0 for start, 1 for end, 2 for intermediate

class SprayWallBloc(BaseModel):
    description: Optional[str] = ""
    grade_id: str
    holds: Optional[List[SprayWallHold]] = [] # list of ids of the holds
    date: Optional[str] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name : Optional[str] = ""
    attributes : Optional[List[str]] = []
    equivalentExte : Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value
