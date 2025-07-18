from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from typing import Optional, List, Union
from ..User.deps import get_current_user
from datetime import datetime

from .model import *


@app.post("/api/v1/partners/", response_model=PartnerReturn)
async def create_partner(partner: Partner, user=Depends(get_current_user)):
    partner = partner.dict()
    partner["created_at"] = datetime.now().isoformat()
    partner_id = firestore_db.collection("partners").document().id
    firestore_db.collection("partners").document(partner_id).set(partner)
    partner["id"] = partner_id
    return partner


@app.get("/api/v1/partners/", response_model=List[PartnerReturn] | PartnerReturn)
async def get_partners(partner_id: Optional[str] = None):
    if partner_id is not None:
        print(partner_id)
        partner = firestore_db.collection("partners").document(partner_id).get()
        if partner.exists:
            partner_dict = partner.to_dict()
            partner_dict["id"] = partner_id
            return partner_dict
        else:
            raise HTTPException(status_code=404, detail="Partner not found")
    partners = firestore_db.collection("partners").stream()
    partners_list = []
    for partner in partners:
        id = partner.id
        partner_dict = partner.to_dict()
        partner_dict["id"] = id
        partners_list.append(partner_dict)
    return partners_list

@app.post("/api/v1/partners/{partner_id}/products/", response_model=ProductReturn)
async def create_partner_product(partner_id: str, product: Product, user=Depends(get_current_user)):
    partner = firestore_db.collection("partners").document(partner_id).get()
    if not partner.exists:
        raise HTTPException(status_code=404, detail="Partner not found")
    product = product.dict()
    product_id = firestore_db.collection('partners').document(partner_id).collection('products').document().id
    firestore_db.collection('partners').document(partner_id).collection('products').document(product_id).set(product)
    product['id'] = product_id
    product['partner'] = partner.to_dict() 
    product['partner']['id'] = partner_id
    return product
