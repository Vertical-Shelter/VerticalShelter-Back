import datetime
from typing import List, Optional

from pydantic import BaseModel, model_validator

class NewsDB(BaseModel):
    news_type: str # NEW FRIENDS etc
    topic: str
    title_payload: str
    body_payload: str
    image_url: Optional[str] = None
    args: Optional[dict] = None
    date: datetime.datetime

class NewsResp(BaseModel):
    id: str
    news_type: str
    topic: str
    title: str
    description: str
    image_url: Optional[str] = None
    args: Optional[dict] = None
    is_read: bool = False
    date: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if "date" in value and isinstance(value["date"], datetime.datetime):
            value["date"] = value["date"].isoformat().replace("+00:00", "Z")
        return value
