from ...settings import firestore_db,   storage_client, BUCKET_NAME, app, pyrebase
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from typing import Optional, List, Union
from ...User.deps import get_current_user
from datetime import datetime, timedelta
from google.cloud import firestore
from .models import *

#Create quete 
@app.post("/api/v1/season_pass/{season_pass_id}/quetes_quotidienne/", response_model=QueteReturn)
def create_quete_quotidienne(quete: Quete,season_pass_id : str,  user = Depends(get_current_user)):

    seasonPass_ref = firestore_db.collection('season_pass').document(season_pass_id)

    if not seasonPass_ref.get().exists:
        raise HTTPException(status_code=400, detail="Season pass not found")

    quete = quete.dict()
    quete_id = seasonPass_ref.collection('quetes_quotidienne').document().id
    seasonPass_ref.collection('quetes_quotidienne').document(quete_id).set(quete)
    quete['id'] = quete_id
    return quete

@app.post("/api/v1/season_pass/{season_pass_id}/quetes_hebdo/", response_model=QueteReturn)
def create_quete_quotidienne(quete: Quete,season_pass_id : str,  user = Depends(get_current_user)):

    seasonPass_ref = firestore_db.collection('season_pass').document(season_pass_id)

    if not seasonPass_ref.get().exists:
        raise HTTPException(status_code=400, detail="Season pass not found")

    quete = quete.dict()
    quete_id = seasonPass_ref.collection('quetes_hebdo').document().id
    seasonPass_ref.collection('quetes_hebdo').document(quete_id).set(quete)
    quete['id'] = quete_id
    return quete


@app.post("/api/v1/season_pass/{season_pass_id}/quetes_unique/", response_model=QueteReturn)
def create_quete_unique(quete: Quete,season_pass_id : str,  user = Depends(get_current_user)):

    seasonPass_ref = firestore_db.collection('season_pass').document(season_pass_id)

    if not seasonPass_ref.get().exists:
        raise HTTPException(status_code=400, detail="Season pass not found")

    quete = quete.dict()
    quete_id = seasonPass_ref.collection('quetes_unique').document().id
    seasonPass_ref.collection('quetes_unique').document(quete_id).set(quete)
    quete['id'] = quete_id
    return quete

# Get user quetes
@app.get("/api/v1/user/quetes_quotidienne/", response_model=List[UserQuete])
def daily_quete_user(user_id : str = Depends(get_current_user)):

    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).get()
    if not user_season_pass.exists:
        #create user season pass
        user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).set({
            "xp": 0,
            "level": 0
        })

    #get user quetes daily
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_quotidienne')
    date = datetime.now().strftime("%Y-%m-%d")
    print(date)
    user_quetes = user_ref.where('date', '==', date).stream()
    user_quetes = list(user_quetes)
    if len(user_quetes) == 0:
        #create user quetes daily
        quetes = firestore_db.collection('season_pass').document(season_pass['id']).collection('quetes_quotidienne').stream()
        quetes = list(quetes)
        res = []
        if len(quetes) == 0:
            raise HTTPException(status_code=400, detail="Quetes not found")
        for quete in quetes:
            queteres = {
               "quete_ref": quete.reference,
               "quota": 0,
                "date": date,
            }
            ref = user_ref.document()
            ref.set(queteres)
            queteres['id'] = ref.id
            queteres['queteId'] = quete.to_dict()
            queteres['queteId']['id'] = quete.id
            res.append(queteres)
        return res
    else:
        quetes = user_quetes
        res = []
        for user_quete in quetes:
            id = user_quete.id
            user_quete = user_quete.to_dict()
            quete_id = user_quete["quete_ref"].id
            quete_ref = user_quete["quete_ref"].get().to_dict()
            quete_ref["id"] = quete_id
            is_claimable = False
            if user_quete['quota'] >= quete_ref['quota']:
                is_claimable = True
            dict = {
                "queteId" : quete_ref,
                "id" : id,
                "quota" : user_quete['quota'],
                "date" : user_quete['date'],
                "is_claimed" : user_quete['is_claimed'] if 'is_claimed' in user_quete else False,
                "is_claimable" : is_claimable
            }
            res.append(dict)
        return res

@app.get("/api/v1/user/quetes_unique/", response_model=List[UserQuete])
def unique_quete_user(user_id : str = Depends(get_current_user)):

    # #get season pass actif 
    # season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    # season_pass_list = []
    # for season_pass in season_pass:
    #     id = season_pass.id
    #     season_pass_dict = season_pass.to_dict()
    #     season_pass_dict['id'] = id
    #     season_pass_list.append(season_pass_dict)
    
    # if len(season_pass_list) == 0:
    #     raise HTTPException(status_code=400, detail="Season pass not found")
    
    # season_pass = season_pass_list[0]
    # #get the user season pass
    # user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).get()
    # if not user_season_pass.exists:
    #     #create user season pass
    #     user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).set({
    #         "xp": 0,
    #         "level": 0
    #     })

    # #get user quetes daily
    # user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_unique')
    # quetes = firestore_db.collection('season_pass').document(season_pass['id']).collection('quetes_unique').stream()
    # quetes = list(quetes)
    # res = []
    # if len(quetes) == 0:
    #     raise HTTPException(status_code=400, detail="Quetes not found")
    # for quete in quetes:
    #     user_quete = user_ref.where('quete_ref', '==', quete.reference).stream()
    #     user_quete = list(user_quete)
    #     print(user_quete)
    #     if (len(list(user_quete)) > 0):
    #         user_quete = user_quete[0]
    #         id = user_quete.id
    #         user_quete = user_quete.to_dict()
    #         quete_id = user_quete["quete_ref"].id
    #         quete_ref = user_quete["quete_ref"].get().to_dict()
    #         quete_ref["id"] = quete_id
    #         is_claimable = False
    #         if user_quete['quota'] >= quete_ref['quota']:
    #             is_claimable = True
    #         dict = {
    #             "queteId" : quete_ref,
    #             "id" : id,
    #             "quota" : user_quete['quota'],
    #             "date" : user_quete['date'],
    #             "is_claimed" : user_quete['is_claimed'] if 'is_claimed' in user_quete else False,
    #             "is_claimable" : is_claimable
    #         }
    #         res.append(dict)
    #     else:
    #         queteres = {
    #             "quete_ref": quete.reference,
    #             "quota": 0,
    #             "date": datetime.now().strftime("%Y-%m-%d"),
    #         }
    #         ref = user_ref.document()
    #         ref.set(queteres)
    #         queteres['id'] = ref.id
    #         queteres['queteId'] = quete.to_dict()
    #         queteres['queteId']['id'] = quete.id
    #         res.append(queteres)
    return []

@app.get("/api/v1/user/quetes_hebdo/", response_model=List[UserQuete])
def hebdo_quete_user(user_id : str = Depends(get_current_user)):
     #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).get()
    if not user_season_pass.exists:
        #create user season pass
        user_season_pass = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).set({
            "xp": 0,
            "level": 0
        })

    #get user quetes daily
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_hebdo')
    #get the monday before the current date
    date = datetime.now()
    date = date - timedelta(days=date.weekday())
    date = date.strftime("%Y-%m-%d")
    user_quetes = user_ref.where('date', '>=', date).stream()
    user_quetes = list(user_quetes)
    if len(user_quetes) == 0:
        #create user quetes daily
        quetes = firestore_db.collection('season_pass').document(season_pass['id']).collection('quetes_hebdo').stream()
        quetes = list(quetes)
        res = []
        if len(quetes) == 0:
            raise HTTPException(status_code=400, detail="Quetes not found")
        for quete in quetes:
            queteres = {
               "quete_ref": quete.reference,
               "quota": 0,
                "date": date,
            }
            ref = user_ref.document()
            ref.set(queteres)
            queteres['id'] = ref.id
            queteres['queteId'] = quete.to_dict()
            queteres['queteId']['id'] = quete.id
            res.append(queteres)
        return res
    else:
        quetes = user_quetes
        res = []
        for user_quete in quetes:
            id = user_quete.id
            user_quete = user_quete.to_dict()
            quete_id = user_quete["quete_ref"].id
            quete_ref = user_quete["quete_ref"].get().to_dict()
            quete_ref["id"] = quete_id
            is_claimable = False
            if user_quete['quota'] >= quete_ref['quota']:
                is_claimable = True
            dict = {
                "queteId" : quete_ref,
                "id" : id,
                "quota" : user_quete['quota'],
                "date" : user_quete['date'],
                "is_claimed" : user_quete['is_claimed'] if 'is_claimed' in user_quete else False,
                "is_claimable" : is_claimable
            }
            res.append(dict)
        return res
    
#Claim quete
@app.post("/api/v1/user/quetes_quotidienne/{quete_id}/claim/")
def claim_quete_quo(quete_id : str, user_id : str = Depends(get_current_user)):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists:
        #the user has not the season pass
        raise HTTPException(status_code=400, detail="User has not the season pass")
    

    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_quotidienne')
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=400, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
     
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        raise HTTPException(status_code=400, detail="Quete already claimed")
    
    if user_quete['quota'] < season_pass_quete['quota']:
        raise HTTPException(status_code=400, detail="Quete not completed")
   
    
    #claim the quete
    
    user_ref.document(quete_id).update(
        {
            "is_claimed": True
        }
    )

    #add xp to the user
    user_season_pass_ref.update(
        {
            "xp": firestore.Increment(season_pass_quete['xp'])
        }
    )

    #check if the user has leveled up
    # check his current level
    user_season_pass = user_season_pass_ref.get().to_dict()
    user_levels = user_season_pass_ref.collection('level').stream()
    user_levels = list(user_levels)
    user_level = len(user_levels)

    #get the xp needed to level up in the sp
    levels = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (user_level+1)).stream()
    levels = list(levels)
    if len(levels) == 0:
        raise HTTPException(status_code=400, detail="Level not found")
    level_id = levels[0].id
    level = levels[0].to_dict()
    if user_season_pass['xp'] >= level['xp']:
        #level up
        xp = user_season_pass['xp']
        while xp >= level['xp']:
            xp = xp - level['xp']
            user_season_pass_ref.collection('level').document(level_id).set(
                {
                    'is_Free_unlock': True,
                    'is_Premium_unlock': user_season_pass['is_premium'] if 'is_premium' in user_season_pass else False,
                    'date_Free_claimed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            )
            level = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (level['numero']+1)).stream()
            level = list(level)
            if len(level) == 0:
                break
            level_id = level[0].id
            level = level[0].to_dict()
        user_season_pass_ref.update(
            {
                "level": level['numero'] - 1,
                "xp": xp,
            }
        )
    return {"quetes" : 'claim'}
    
@app.post("/api/v1/user/quetes_hebdo/{quete_id}/claim/")
def claim_quete_hebdo(quete_id : str, user_id : str = Depends(get_current_user)):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists:
        #the user has not the season pass
        raise HTTPException(status_code=400, detail="User has not the season pass")
    

    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_hebdo')
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=400, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
     
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        raise HTTPException(status_code=400, detail="Quete already claimed")
    
    if user_quete['quota'] < season_pass_quete['quota']:
        raise HTTPException(status_code=400, detail="Quete not completed")
   
    
    #claim the quete
    
    user_ref.document(quete_id).update(
        {
            "is_claimed": True
        }
    )

    #add xp to the user
    user_season_pass_ref.update(
        {
            "xp": firestore.Increment(season_pass_quete['xp'])
        }
    )

    # check his current level
    user_season_pass = user_season_pass_ref.get().to_dict()
    level = user_season_pass['level']
    #get the xp needed to level up in the sp
    levels = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (level+1)).stream()
    levels = list(levels)
    if len(levels) == 0:
        raise HTTPException(status_code=400, detail="Level not found")
    level_id = levels[0].id
    level = levels[0].to_dict()
    print(level)
    if user_season_pass['xp'] >= level['xp']:
        #level up
        xp = user_season_pass['xp']
        while xp >= level['xp']:
            print(level['numero'])
            print(level['xp'])
            print(xp)
            xp = xp - level['xp']
            user_season_pass_ref.update(
                {
                    "level": firestore.Increment(1),
                    "xp": xp,
                }
            )
            user_season_pass_ref.collection('level').document(level_id).set(
                {
                    'is_Free_unlock': True,
                    'is_Premium_unlock': user_season_pass['is_premium'] if 'is_premium' in user_season_pass else False,
                    'date_Free_claimed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            )
            level = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (level['numero']+1)).stream()
            level = list(level)
            if len(level) == 0:
                break
            level_id = level[0].id
            level = level[0].to_dict()
           
    return {"quetes" : 'claim'}

@app.post("/api/v1/user/quetes_unique/{quete_id}/claim/")
def claim_quetes_unique(quete_id : str, user_id : str = Depends(get_current_user)):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists:
        #the user has not the season pass
        raise HTTPException(status_code=400, detail="User has not the season pass")
    

    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_unique')
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=400, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
     
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        raise HTTPException(status_code=400, detail="Quete already claimed")
    
    if user_quete['quota'] < season_pass_quete['quota']:
        raise HTTPException(status_code=400, detail="Quete not completed")
   
    
    #claim the quete
    
    user_ref.document(quete_id).update(
        {
            "is_claimed": True
        }
    )

    #add xp to the user
    user_season_pass_ref.update(
        {
            "xp": firestore.Increment(season_pass_quete['xp'])
        }
    )

    # check his current level
    user_season_pass = user_season_pass_ref.get().to_dict()
    level = user_season_pass['level']
    #get the xp needed to level up in the sp
    levels = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (level+1)).stream()
    levels = list(levels)
    if len(levels) == 0:
        raise HTTPException(status_code=400, detail="Level not found")
    level_id = levels[0].id
    level = levels[0].to_dict()
    print(level)
    if user_season_pass['xp'] >= level['xp']:
        #level up
        xp = user_season_pass['xp']
        while xp >= level['xp']:
            xp = xp - level['xp']
            user_season_pass_ref.update(
                {
                    "level": firestore.Increment(1),
                    "xp": xp,
                }
            )
            user_season_pass_ref.collection('level').document(level_id).set(
                {
                    'is_Free_unlock': True,
                    'is_Premium_unlock': user_season_pass['is_premium'] if 'is_premium' in user_season_pass else False,
                    'date_Free_claimed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            )
            level = firestore_db.collection('season_pass').document(season_pass['id']).collection('level').where('numero', '==', (level['numero']+1)).stream()
            level = list(level)
            if len(level) == 0:
                break
            level_id = level[0].id
            level = level[0].to_dict()
           
    return {"quetes" : 'claim'}

@app.patch("/api/v1/user/quetes_unique/{quete_id}/increment/")
def increment_quete_unique(quete_id : str, user_id : str = Depends(get_current_user)):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists:
        #the user has not the season pass
        raise HTTPException(status_code=400, detail="User has not the season pass")
    

    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_unique')
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=400, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
     
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        raise HTTPException(status_code=400, detail="Quete already claimed")
    if user_quete['quota'] >= season_pass_quete['quota']:
        raise HTTPException(status_code=400, detail="Quete already completed")
   
    #increment the quete
    
    user_ref.document(quete_id).update(
        {
            "quota": firestore.Increment(1)
        }
    )