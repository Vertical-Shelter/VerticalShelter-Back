from datetime import datetime

import pandas as pd
from settings import firestore_db,   storage_client, BUCKET_NAME, app, pyrebase
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from User.deps import get_current_user
from concurrent.futures import ThreadPoolExecutor
from Season_Pass.model import *
from google.cloud import firestore

@app.post("/api/v1/user/me/season_pass/{season_pass_id}/level/{level_id}/recompense/")
def get_level(season_pass_id: str,level_id : str, recompense_type : str, userId : str = Depends(get_current_user)):

    if (recompense_type != 'recompense_G' and recompense_type != 'recompense_P'):
        raise HTTPException(status_code=400, detail="recompense type not found")
    user_sp = firestore_db.collection('users').document(userId).collection('season_pass').document(season_pass_id).get().to_dict()
    if user_sp is None:
        raise HTTPException(status_code=400, detail="User Season pass not found")
    
    season_pass = firestore_db.collection('season_pass').document(season_pass_id).get().to_dict()
    if season_pass is None:
        raise HTTPException(status_code=400, detail="Season pass not found")
    
    level = firestore_db.collection('season_pass').document(season_pass_id).collection('level').document(level_id).get()
    if level.exists is False:
        raise HTTPException(status_code=400, detail="Level not found")
    
    status = firestore_db.collection('users').document(userId).collection('season_pass').document(season_pass_id).collection('level').document(level_id).get().to_dict()
    if (status == None):
        return {
            'status': 'locked'
        }
    print(status)
    if recompense_type == 'recompense_G' and status['is_Free_unlock'] == True and (not 'is_Free_claimed' in status or status['is_Free_claimed'] == False):
        recompenses_ref = level.reference.get().to_dict()['recompense_G']
        recompenses = recompenses_ref.get().to_dict()
        free_promotion = None
        if recompenses['recompense_type'] == 'Coins'  :
            
            firestore_db.collection('users').document(userId).update(
                {
                    'coins' : firestore.Increment(int(recompenses['promotion']))
                }
            )
            free_promotion = str(recompenses['promotion']) + " coins ajouté à votre compte"
        if recompenses['recompense_type'] == 'Badge'  :
            #need to get the badge id

            print(recompenses['name'])
            badge_ref = firestore_db.collection('baniere').where('name', '==', recompenses['name']).stream()
            badge_ref = list(badge_ref)
            if len(badge_ref) == 0:
                raise HTTPException(status_code=400, detail="Badge not found")
            badge_ref = badge_ref[0].reference

            firestore_db.collection('users').document(userId).update(
                {
                    'all_banieres' : firestore.ArrayUnion([badge_ref])
                }
            )
            free_promotion = "Badge ajouté à votre collection"
        if recompenses['recompense_type'] == 'Avatar'  :
            #need to get the avatar id
            avatar_ref = firestore_db.collection('avatar').where('name', '==', recompenses['name']).stream()
            avatar_ref = list(avatar_ref)
            if len(avatar_ref) == 0:
                raise HTTPException(status_code=400, detail="Badge not found")
            avatar_ref = avatar_ref[0].reference
            firestore_db.collection('users').document(userId).update(
                {
                    'all_avatars' : firestore.ArrayUnion([avatar_ref])
                }
            )
            free_promotion = "Maitre ajouté à votre collection"
        if recompenses['recompense_type'] == 'unique' :
            free_promotion = recompenses['recompense_file']
        if recompenses['recompense_type'] == 'show' :
            free_promotion = 'SHOW'
        if recompenses['recompense_type'] == 'file' :
            free_promotion = recompenses['recompense_file']

        firestore_db.collection('users').document(userId).collection('season_pass').document(season_pass_id).collection('level').document(level_id).update(
            {
                'free_Promotion' : free_promotion,
                'is_Free_claimed': True,
                'date_Free_claimed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        )
    elif recompense_type == 'recompense_P' and status['is_Premium_unlock'] == True and (not 'is_Premium_claimed' in status or status['is_Premium_claimed'] == False):
        print('premium')
        recompenses_ref = level.reference.get().to_dict()['recompense_P']
        recompenses = recompenses_ref.get().to_dict()
        premium_promotion = None
        if recompenses['name'] == 'Coins'  :
            
            firestore_db.collection('users').document(userId).update(
                {
                    'coins' : firestore.Increment(int(recompenses['promotion']))
                }
            )
        if recompenses['name'] == 'Badge'  :
            #need to get the badge id
            print(recompenses['product_url'])
            badge_ref = firestore_db.collection('baniere').where('name', '==', recompenses['product_url']).stream()
            badge_ref = list(badge_ref)
            if len(badge_ref) == 0:
                raise HTTPException(status_code=400, detail="Badge not found")
            badge_ref = badge_ref[0].reference

            firestore_db.collection('users').document(userId).update(
                {
                    'all_banieres' : firestore.ArrayUnion([badge_ref])
                }
            )
            premium_promotion = "Badge ajouté à votre collection"
        if recompenses['name'] == 'Avatar'  :
            #need to get the avatar id
            avatar_ref = firestore_db.collection('avatar').where('name', '==', recompenses['product_url']).stream()
            avatar_ref = list(avatar_ref)
            if len(avatar_ref) == 0:
                raise HTTPException(status_code=400, detail="Badge not found")
            avatar_ref = avatar_ref[0].reference
            firestore_db.collection('users').document(userId).update(
                {
                    'all_avatars' : firestore.ArrayUnion([avatar_ref])
                }
            )
            premium_promotion = "Maitre ajouté à votre collection"
        if recompenses['recompense_type'] == 'unique' :
            premium_promotion = recompenses['recompense_file']
        if recompenses['recompense_type'] == 'show' :
            premium_promotion = 'Récompense déja utilisée'
        if recompenses['recompense_type'] == 'file' :
            index = recompenses['index'] if 'index' in recompenses else 0
            code = getCodeatIndex(recompenses['recompense_file'], index)
            #update index of the partner
            recompenses_ref.update(
                {
                    'index' : firestore.Increment(1)
                }
            )
            premium_promotion = code
        firestore_db.collection('users').document(userId).collection('season_pass').document(season_pass_id).collection('level').document(level_id).update(
            {
                'premium_Promotion' : premium_promotion,
                'is_Premium_claimed': True,
                'date_Premium_claimed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        )
    return firestore_db.collection('users').document(userId).collection('season_pass').document(season_pass_id).collection('level').document(level_id).get().to_dict()

def getCodeatIndex(file_path, index):
    #change the line in the csv file
    df = pd.read_csv(file_path, delimiter=';')
    #get the value CODE in the index

    return df['Code'][index]
