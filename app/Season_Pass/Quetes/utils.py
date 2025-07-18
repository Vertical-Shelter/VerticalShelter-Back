from datetime import timedelta
from ...settings import firestore_db,   storage_client, BUCKET_NAME, app
from fastapi.exceptions import HTTPException
from google.cloud import firestore
from .models import *
#import filter


def increment_quete_quo(quete_name : str, user_id : str ):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        print("Season pass not found")
        return None
    isQueteQuo = True
    isQueteHebdo = True
    #Quetes Quotidienne
    queteQuo_ref = firestore_db.collection('season_pass').document(season_pass_list[0]['id']).collection('quetes_quotidienne').where('title', '==', quete_name).stream()
    queteQuo_ref = list(queteQuo_ref)
    if len(queteQuo_ref) == 0:
        print("Quete not found in SP")
        isQueteQuo  = False
    queteQuo_ref = queteQuo_ref[0]

    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists :
        #the user has not the season pass
        print("User has not the season pass")
        return None
    
    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_quotidienne')
    user_quete = user_ref.where('quete_ref', '==', queteQuo_ref.reference).where('date', '==', datetime.now().strftime("%Y-%m-%d")).stream()
    user_quete = list(user_quete)
    print(datetime.now().strftime("%Y-%m-%d"))
    if len(user_quete) == 0:
        isQueteQuo = False
    quete_id = user_quete[0].id

    user_quete = user_quete[0].to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        isQueteQuo  = False
    
    if user_quete['quota'] >= season_pass_quete['quota']:
        isQueteQuo  = False
   
    #increment the quete
    if isQueteQuo:
        user_ref.document(quete_id).update(
            {
                "quota": firestore.Increment(1)
            }
        )

    #Quete Hebdo
    
    queteHebdo_ref = firestore_db.collection('season_pass').document(season_pass_list[0]['id']).collection('quetes_hebdo').where('title', '==', quete_name).stream()
    queteHebdo_ref = list(queteHebdo_ref)
    if len(queteHebdo_ref) == 0:
        print("Quete not found in SP")
        isQueteHebdo  = False
    queteHebdo_ref = queteHebdo_ref[0]

    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists :
        #the user has not the season pass
        print("User has not the season pass")
        return None
    def filterDateAndRef(x):
        date = datetime.now()
        date = date - timedelta(days=date.weekday())
        date = date.strftime("%Y-%m-%d")
        x = x.to_dict()
      
        return x['date'] >= date and x['quete_ref'] == queteHebdo_ref.reference
    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_hebdo')
    
    user_quete = filter(filterDateAndRef, user_ref.stream())
    user_quete = list(user_quete)
    #get user quete where date is the first day of the week
    if len(user_quete) == 0:
        isQueteHebdo = False

    ##########################################"" BUG ICI
    #find user where quete_ref is equal to queteHebdo_ref and date is the first day of the week
    quete_id = user_quete[0].id

    user_quete = user_quete[0].to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()

    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        isQueteHebdo = False
    
    if user_quete['quota'] >= season_pass_quete['quota']:
        isQueteHebdo = False
   
    #increment the quete
    if isQueteHebdo:
        user_ref.document(quete_id).update(
            {
                "quota": firestore.Increment(1)
            }
        )
        
def increment_quete_unique(quete_name, user_id):
    #get season pass actif 
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        print("Season pass not found")
        return None
    isQueteQuo = True
    isQueteHebdo = True
    #Quetes Quotidienne
    queteQuo_ref = firestore_db.collection('season_pass').document(season_pass_list[0]['id']).collection('quetes_unique').where('title', '==', quete_name).stream()
    queteQuo_ref = list(queteQuo_ref)
    if len(queteQuo_ref) == 0:
        print("Quete not found in SP")
        isQueteQuo  = False
    queteQuo_ref = queteQuo_ref[0]

    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists :
        #the user has not the season pass
        print("User has not the season pass")
        return None
    
    #get the user quete
    user_ref = firestore_db.collection('users').document(user_id).collection('season_pass').document(season_pass['id']).collection('quetes_unique')
    user_quete = user_ref.where('quete_ref', '==', queteQuo_ref.reference).where('date', '==', datetime.now().strftime("%Y-%m-%d")).stream()
    user_quete = list(user_quete)
    print(datetime.now().strftime("%Y-%m-%d"))
    if len(user_quete) == 0:
        isQueteQuo = False
    quete_id = user_quete[0].id

    user_quete = user_quete[0].to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        isQueteQuo  = False
    
    if user_quete['quota'] >= season_pass_quete['quota']:
        isQueteQuo  = False
   
    #increment the quete
    if isQueteQuo:
        user_ref.document(quete_id).update(
            {
                "quota": firestore.Increment(1)
            }
        )