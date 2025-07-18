from pydantic import BaseModel, model_validator
from ..Partenaires.model import Partner, PartnerReturn, Product, ProductReturn
from ..settings import firestore_db


class Level(BaseModel):
    numero : int
    xp : int
    recompense_G : str | None = None
    recompense_P : str | None = None

class LevelReturn(Level):
    #read_only
    id : str
    recompense_G : ProductReturn | None = None
    recompense_P : ProductReturn 
    is_Premium_unlock: bool | None = None,
    is_Free_unlock: bool = False,
    isPremiumClaimed: bool = False,
    isFreeClaimed: bool  = False,
    free_Promotion: str  | None = None,
    premium_Promotion: str | None = None,

class SeasonPass(BaseModel):
    title: str
    image_url: str
    description: str
    date_start: str
    date_end: str
    price: float
    is_active: bool = False


class SeasonPassReturn(SeasonPass):
    #read_only
    id : str
    levels : list[LevelReturn] = []
    level : int = 0
    xp : int = 0
    # xp_to_next_level : int = 0
    is_premium : bool = False
