from fastapi import FastAPI, Form,HTTPException, Depends, File, UploadFile
from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from .gameObject import *
from ..User.deps import get_current_user
from google.cloud import firestore

#Avatar api

@app.post("/api/v1/avatar/")
async def createAvatar(
    avatar : Avatar = Form(...),
    avatar_file : UploadFile = File(...)    
):
    #upload avatar
    blob = storage_client.bucket(BUCKET_NAME).blob('avatar/' + avatar.name)
    blob.upload_from_file(avatar_file.file)
    avatar_url = blob.public_url

    firestore_db.collection('avatar').add({
        'avatar_url': avatar_url,
        'name' : avatar.name,
        'description' : avatar.description,
        'price' : avatar.price,
        'is_active' : avatar.is_active
    })

    return {'avatar': avatar_url}

@app.get("/api/v1/avatar/", response_model=list[AvatarReturn])
async def getAvatar(
    user_id : str = Depends(get_current_user),
):
    avatars = firestore_db.collection('avatar').stream()
    avatars_list = []
    user_ref = firestore_db.collection('users').document(user_id).get().to_dict()
    if user_ref is None:
        raise HTTPException(status_code=400, detail="User not found")
    for avatar in avatars:
        avatar_dict = avatar.to_dict()
        avatar_dict['id'] = avatar.id
        if 'all_avatars' in user_ref and avatar.reference in user_ref['all_avatars']:
            avatar_dict['isBought'] = True
        else:
            avatar_dict['isBought'] = False
        if 'avatar' in user_ref and avatar.reference == user_ref['avatar']:
            avatar_dict['isEquiped'] = True
        else:
            avatar_dict['isEquiped'] = False
        if avatar_dict['is_active']:
            avatars_list.append(avatar_dict)
    avatars_list.sort(key=lambda x: x['price'])
    return avatars_list

#buy avatar
@app.post("/api/v1/avatar/buy/", response_model=AvatarReturn)
async def buyAvatar(
    avatar_id : str,
    user_id : str = Depends(get_current_user),
):
    avatar_ref = firestore_db.collection('avatar').document(avatar_id)
    avatar = avatar_ref.get()
    if not avatar.exists:
        raise HTTPException(status_code=400, detail="Avatar not found")
    avatar_dict = avatar.to_dict()
    if not avatar_dict['is_active']:
        raise HTTPException(status_code=400, detail="Avatar not available")
    user_ref = firestore_db.collection('users').document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=400, detail="User not found")
    user_dict = user.to_dict()
     
    if'all_avatars' in user_dict and avatar_ref in user_dict['all_avatars']:
        raise HTTPException(status_code=400, detail="Avatar already bought")
    if not 'coins' in user_dict or user_dict['coins'] < avatar_dict['price']:
        nb_coins = 0
        if 'coins' in user_dict:
            nb_coins = user_dict['coins']
        raise HTTPException(status_code=400, detail="Il te manque des mousquettes : "+str(nb_coins)+" < "+str(avatar_dict['price'])+" coins ")
   
    if 'all_avatars' in user_dict:
        user_ref.update({
            'coins': firestore.Increment(-avatar_dict['price']),
            'avatar': avatar_ref,
            'all_avatars': firestore.ArrayUnion([avatar_ref])
        })
    else:
        user_ref.update({
            'coins': firestore.Increment(-avatar_dict['price']),
            'avatar': avatar_ref,
            'all_avatars': [avatar_ref]
        })
    avatar_dict['id'] = avatar.id
    avatar_dict['isBought'] = True
    avatar_dict['isEquiped'] = True
    return avatar_dict


#select avatar
@app.post("/api/v1/user/avatar/select/", response_model=AvatarReturn)
async def selectAvatar(
    avatar_id : str,
    user_id : str = Depends(get_current_user),
):
    avatar_ref = firestore_db.collection('avatar').document(avatar_id)
    avatar = avatar_ref.get()
    if not avatar.exists:
        raise HTTPException(status_code=400, detail="Avatar not found")
    avatar_dict = avatar.to_dict()
    if not avatar_dict['is_active']:
        raise HTTPException(status_code=400, detail="Avatar not available")
    user_ref = firestore_db.collection('users').document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=400, detail="User not found")
    if avatar_ref not in user.to_dict()['all_avatars']:
        raise HTTPException(status_code=400, detail="Avatar not bought")
    user_dict = user.to_dict()
    if 'avatar' in user_dict:
        user_ref.update({
            'avatar': avatar_ref
        })
        avatar_dict['id'] = avatar.id
        avatar_dict['isBought'] = True
        avatar_dict['isEquiped'] = True
        return avatar_dict
    else:
        raise HTTPException(status_code=400, detail="Avatar not bought")
    

#get my avatars
@app.get("/api/v1/user/avatar/", response_model=list[AvatarReturn])
def getMyAvatars(
    user_id : str = Depends(get_current_user),
):
    user_ref = firestore_db.collection('users').document(user_id).get().to_dict()
    if 'all_avatars' not in user_ref:
        return []
    avatars = user_ref['all_avatars']
    avatars_list = []
    for avatar in avatars:
        avatar_dict = avatar.get().to_dict()
        avatar_dict['id'] = avatar.id
        avatar_dict['isBought'] = True
        if 'avatar' in user_ref and avatar == user_ref['avatar']:
            avatar_dict['isEquiped'] = True
        else:
            avatar_dict['isEquiped'] = False
        if avatar_dict['is_active']:
            avatars_list.append(avatar_dict)
    return avatars_list