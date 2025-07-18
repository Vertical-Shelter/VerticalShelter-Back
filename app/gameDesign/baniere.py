from fastapi import FastAPI, Form,HTTPException, Depends, File, UploadFile
from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from .gameObject import *
from google.cloud import firestore
from ..User.deps import get_current_user
#banieres api

@app.post("/api/v1/baniere/")
async def createBaniere(
    baniere : Baniere = Form(...),
    baniere_file : UploadFile = File(...)    
):
    #upload baniere
    blob = storage_client.bucket(BUCKET_NAME).blob('baniere/' + baniere.name)
    blob.upload_from_file(baniere_file.file)
    baniere_url = blob.public_url
    
    firestore_db.collection('baniere').add({
        'baniere_url': baniere_url,
        'name' : baniere.name,
        'description' : baniere.description,
        'price' : baniere.price,
        'is_active' : baniere.is_active
    })

    return {'baniere': baniere_url}

@app.get("/api/v1/baniere/", response_model=list[BaniereReturn])
async def getBaniere(
    user_id : str = Depends(get_current_user),
):
    banieres = firestore_db.collection('baniere').stream()
    banieres_list = []
    user_ref = firestore_db.collection('users').document(user_id).get().to_dict()
    if user_ref is None:
        raise HTTPException(status_code=400, detail="User not found")
    for baniere in banieres:
        baniere_dict = baniere.to_dict()
        baniere_dict['id'] = baniere.id
        baniere_url = baniere_dict['image_url']
        baniere_dict['baniere_url'] = baniere_url
        if 'all_banieres' in user_ref and baniere.reference in user_ref['all_banieres']:
            baniere_dict['isBought'] = True
        else:
            baniere_dict['isBought'] = False
        if 'baniere' in user_ref and baniere.reference == user_ref['baniere']:
            baniere_dict['isEquiped'] = True
        else:
            baniere_dict['isEquiped'] = False
        if baniere_dict['is_active']:
            banieres_list.append(baniere_dict)
    banieres_list.sort(key=lambda x: x['price'])
    return banieres_list

#buy baniere
@app.post("/api/v1/baniere/buy/", response_model=BaniereReturn)
async def buyBaniere(
    baniere_id : str,
    user_id : str = Depends(get_current_user),
):
    baniere_ref = firestore_db.collection('baniere').document(baniere_id)
    baniere = baniere_ref.get()
    if not baniere.exists:
        raise HTTPException(status_code=400, detail="Baniere not found")
    baniere_dict = baniere.to_dict()
    if not baniere_dict['is_active']:
        raise HTTPException(status_code=400, detail="Baniere not available")
    user_ref = firestore_db.collection('users').document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=400, detail="User not found")
    user_dict = user.to_dict()
     
    if 'all_banieres' in user_dict and baniere_ref in user_dict['all_banieres']:
        raise HTTPException(status_code=400, detail="Baniere already bought")
    if not 'coins' in user_dict or user_dict['coins'] < baniere_dict['price']:
        nb_coins = 0
        if 'coins' in user_dict:
            nb_coins = user_dict['coins']
        raise HTTPException(status_code=400, detail="Il te manque des mousquettes : "+str(nb_coins)+" < "+str(baniere_dict['price'])+" coins ")
   
    if ('all_banieres' in user_dict):
        user_ref.update({
            'coins': firestore.Increment(-baniere_dict['price']),
            'baniere': baniere_ref,
            'all_banieres': firestore.ArrayUnion([baniere_ref])
        })
    else:
        user_ref.update({
            'coins': firestore.Increment(-baniere_dict['price']),
            'baniere': baniere_ref,
            'all_banieres': [baniere_ref]
        })
    baniere_dict['id'] = baniere.id
    baniere_dict['isBought'] = True
    baniere_dict['isEquiped'] = True
    return baniere_dict


#select baniere
@app.post("/api/v1/user/baniere/select/", response_model=BaniereReturn)
async def selectBaniere(
        baniere_id : str,
    user_id : str = Depends(get_current_user),
):
    baniere_ref = firestore_db.collection('baniere').document(baniere_id)
    baniere = baniere_ref.get()
    if not baniere.exists:
        raise HTTPException(status_code=400, detail="Baniere not found")
    baniere_dict = baniere.to_dict()
    user_ref = firestore_db.collection('users').document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=400, detail="User not found")
    if baniere_ref not in user.to_dict()['all_banieres']:
        raise HTTPException(status_code=400, detail="Baniere not bought")
    user_ref.update({
        'baniere': baniere_ref
    })
    baniere_dict['id'] = baniere.id
    baniere_dict['isBought'] = True
    baniere_dict['isEquiped'] = True
    return baniere_dict  

#get my avatars
@app.get("/api/v1/user/baniere/", response_model=list[BaniereReturn])
def getMyAvatars(
    user_id : str = Depends(get_current_user),
):
    user_ref = firestore_db.collection('users').document(user_id).get().to_dict()
    if 'all_banieres' not in user_ref:
        return []
    banieres = user_ref['all_banieres']
    baniere_list = []
    for baniere in banieres:
        baniere_dict = baniere.get().to_dict()
        baniere_dict['id'] = baniere.id
        baniere_dict['isBought'] = True
        if 'baniere' in user_ref and baniere == user_ref['baniere']:
            baniere_dict['isEquiped'] = True
        else:
            baniere_dict['isEquiped'] = False
        baniere_list.append(baniere_dict)
    return baniere_list