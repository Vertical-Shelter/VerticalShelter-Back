from pydantic import BaseModel, model_validator

class Partner(BaseModel):
    name : str
    description : str
    logo_url : str
    website : str

class PartnerReturn(Partner):
    #read_only
    id : str

recompense_type = ['file', 'unique', 'show', 'contact', 'app']
class Product(BaseModel):
    name : str
    description : str | None = None
    recompense_file : str | None = None
    recompense_type : str | None = None
    image_url : str | None = None
    promotion : str | None = None
    product_url : str | None = None

    # @model_validator
    # def check_recompense_type(cls):
    #     if cls.recompense_type not in recompense_type:
    #         raise ValueError('recompense_type must be one of the following values: file, unique, show')
        
class ProductReturn(Product):
    #read_only
    id : str
    partner : PartnerReturn
