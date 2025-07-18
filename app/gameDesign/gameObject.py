import json
from pydantic import BaseModel, model_validator

class GameObject(BaseModel):
    name : str
    description : str
    type : str
    price : float
    is_active : bool = False
    image_url : str

class Avatar(GameObject):
    type : str = "Avatar"
    
    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            #get only the json part
            return cls(**json.loads(value))
        return value

class AvatarReturn(Avatar):
    #read_only
    id : str
    isBought : bool
    isEquiped : bool

class Baniere(GameObject):
    type : str = "Baniere"    
    
    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            #get only the json part
            return cls(**json.loads(value))
        return value
    
class BaniereReturn(Baniere):
    #read_only
    id : str
    isBought : bool
    isEquiped : bool

