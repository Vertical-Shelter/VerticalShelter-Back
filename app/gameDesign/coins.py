from fastapi import FastAPI, Form,HTTPException, Depends, File, UploadFile
from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from ..User.deps import get_current_user
from google.cloud import firestore

#coins api

#add coins to user

@app.post("/api/v1/user/coins/")
async def addCoins(
    user_id : str = Depends(get_current_user),
    coins : int = Form(...)
):
    print(user_id)
    user_ref = firestore_db.collection('users').document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user_dict = user.to_dict()

    user_ref.update({
        'coins': firestore.Increment(coins)
    })
    return {'coins': 0}