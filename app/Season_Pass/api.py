from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from ..User.deps import get_current_user
from concurrent.futures import ThreadPoolExecutor
from .model import *


@app.post("/api/v1/season_pass/", response_model=SeasonPassReturn)
async def create_season_pass(season_pass: SeasonPass, user=Depends(get_current_user)):
    season_pass = season_pass.dict()
    season_pass_id = firestore_db.collection("season_pass").document().id
    firestore_db.collection("season_pass").document(season_pass_id).set(season_pass)
    season_pass["id"] = season_pass_id

    return season_pass

@app.get("/api/v1/season_pass/", response_model=SeasonPassReturn | None)
async def get_season_pass(user_id : str = Depends(get_current_user)):
    sp = await get_active_season_pass(user_id)
    if sp is None:
        return None
    user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(sp['id']).get()
    sp['user_season_pass'] = user_season_pass.to_dict()
    
    if not user_season_pass.exists:
    #create user season pass
        user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(sp['id']).set({
            "xp": 0,
            "level": 0,
            'is_premium': False,
        })
        sp['user_season_pass'] = {
            "xp": 0,
            "is_premium": False,
            "level": 0,
        }
    else:
        user_season_pass = user_season_pass.to_dict()
        sp['level'] = user_season_pass['level']
        sp['xp'] = user_season_pass['xp']
        sp['is_premium'] = 'is_premium' in user_season_pass and user_season_pass['is_premium'] == True
    return sp

async def get_active_season_pass(user_id):
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []

    def _get_levels(level, season_pass_id, user_id):
        id = level.id
        level_dict = level.to_dict()
        level_dict['id'] = id
        if level_dict['recompense_G'] is not None:
            recompense_G = level_dict['recompense_G'].get().to_dict()
            recompense_G['id'] = level_dict['recompense_G'].id
            recompense_G['partner'] = level_dict['recompense_G'].parent.parent.get().to_dict()
            recompense_G['partner']['id'] = level_dict['recompense_G'].parent.parent.id
            level_dict['recompense_G'] = recompense_G
            
        else:
            level_dict['recompense_G'] = None
        recompense_P = level_dict['recompense_P'].get().to_dict()
        recompense_P['id'] = level_dict['recompense_P'].id
        recompense_P['partner'] = level_dict['recompense_P'].parent.parent.get().to_dict()
        recompense_P['partner']['id'] = level_dict['recompense_P'].parent.parent.id
        level_dict['recompense_P'] = recompense_P

        #get user level
        user_level = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass_id).collection('level').document(id).get()
        if user_level.exists:
            user_level_dict = user_level.to_dict()
            level_dict['isFreeClaimed'] = user_level_dict['is_Free_claimed'] if 'is_Free_claimed' in user_level_dict else False
            level_dict['isPremiumClaimed'] = user_level_dict['is_Premium_claimed'] if 'is_Premium_claimed' in user_level_dict else False
            level_dict['free_Promotion'] = user_level_dict['free_Promotion'] if 'free_Promotion' in user_level_dict else None
            level_dict['is_Free_unlock'] = user_level_dict['is_Free_unlock'] if 'is_Free_unlock' in user_level_dict else False
            level_dict['is_Free_claimed'] = user_level_dict['is_Free_claimed'] if 'is_Free_claimed' in user_level_dict else False
            level_dict['premium_Promotion'] = user_level_dict['premium_Promotion'] if 'premium_Promotion' in user_level_dict else None
            level_dict["is_Premium_unlock"] = user_level_dict['is_Premium_unlock'] if 'is_Premium_unlock' in user_level_dict else False
        else : 
            level_dict['isFreeClaimed'] = False
            level_dict['isPremiumClaimed'] = False
            level_dict['free_Promotion'] = None
            level_dict['is_Free_unlock'] = False
            level_dict['is_Free_claimed'] = False
            level_dict['premium_Promotion'] = None
            level_dict["is_Premium_unlock"] = False
        return level_dict

    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict["id"] = id
        season_pass_list.append(season_pass_dict)
        # get all level
        levels = firestore_db.collection('season_pass').document(id).collection('level').stream()
        levels = list(levels)
        levels_list = []

        with ThreadPoolExecutor() as executor:
            levels_list = list(executor.map(_get_levels, levels, [id]*len(levels), [user_id]*len(levels)))
        levels_list.sort(key=lambda x: x['numero'])
        season_pass_dict['levels'] = levels_list
    if len(season_pass_list) == 0:
        return None
    return season_pass_list[0]


@app.post("/api/v1/season_pass/{season_pass_id}/level/", response_model=SeasonPassReturn)
async def create_season_pass_level(season_pass_id: str, level: Level, user=Depends(get_current_user)):
    season_pass = firestore_db.collection("season_pass").document(season_pass_id).get()
    if not season_pass.exists:
        raise HTTPException(status_code=404, detail="Season pass not found")
    level = level.dict()
    # get product id
    recompense_G = level["recompense_G"]
    recompense_P = level["recompense_P"]
    # get product
    products = firestore_db.collection_group("products").stream()
    products = list(products)
    product_P = None
    product_G = None
    for prod in products:
        if prod.id == recompense_G:
            product_G = prod
            if product_P is not None:
                break
        if prod.id == recompense_P:
            product_P = prod
            if product_G is not None or recompense_G == None:
                break
    if product_P is None:
        raise HTTPException(status_code=404, detail="Product not found")

    level["recompense_G"] = product_G.reference if product_G is not None else None
    level["recompense_P"] = product_P.reference if product_P is not None else None
    level_id = firestore_db.collection("season_pass").document(season_pass_id).collection("level").document().id
    firestore_db.collection("season_pass").document(season_pass_id).collection("level").document(level_id).set(level)
    season_pass_dict = season_pass.to_dict()
    season_pass_dict["id"] = season_pass_id

    # get all level
    levels = firestore_db.collection("season_pass").document(season_pass_id).collection("level").stream()
    levels_list = []
    for level in levels:
        id = level.id
        level_dict = level.to_dict()
        level_dict["id"] = id
        if level_dict["recompense_G"] is not None:
            recompense_G = level_dict["recompense_G"].get().to_dict()
            recompense_G["id"] = level_dict["recompense_G"].id
            level_dict["recompense_G"] = recompense_G
        else:
            level_dict["recompense_G"] = None
        recompense_P = level_dict["recompense_P"].get().to_dict()
        recompense_P["id"] = level_dict["recompense_P"].id
        level_dict["recompense_P"] = recompense_P
        print(level_dict)
        levels_list.append(level_dict)
    season_pass_dict["levels"] = levels_list
    return season_pass_dict


@app.patch("/api/v1/season_pass/{season_pass_id}/set_active/", response_model=SeasonPassReturn)
async def set_active_season_pass(season_pass_id: str, user=Depends(get_current_user)):
    season_pass = firestore_db.collection("season_pass").document(season_pass_id).get()
    if not season_pass.exists:
        raise HTTPException(status_code=404, detail="Season pass not found")
    season_pass.reference.update({
        'is_active': True,
    })
    return seasonPassReturn(season_pass)


def seasonPassReturn(season_pass):
    season_pass_dict = season_pass.to_dict()
    season_pass_dict['id'] = season_pass.id
    levels = firestore_db.collection('season_pass').document(season_pass.id).collection('level').stream()
    levels_list = []
    for level in levels:
        id = level.id
        level_dict = level.to_dict()
        level_dict['id'] = id
        recompense_G = level_dict['recompense_G'].get().to_dict()
        recompense_G['id'] = level_dict['recompense_G'].id
        level_dict['recompense_G'] = recompense_G
        recompense_P = level_dict['recompense_P'].get().to_dict()
        recompense_P['id'] = level_dict['recompense_P'].id
        level_dict['recompense_G'] = recompense_P
        levels_list.append(level_dict)
    season_pass_dict['levels'] = levels_list
    return season_pass_dict
