from ..settings import app, firestore_db
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel
from ..User.deps import get_current_user


@app.post("/api/v1/user/me/FcmToken/")
async def add_fcm_token(fcm_token: str = Form(...), user_id: str = Depends(get_current_user)):
    user = firestore_db.collection("users").document(user_id)
    user.update({"fcm_token": fcm_token})
    return {"detail": "Token added successfully"}


@app.delete("/api/v1/user/me/FcmToken/")
async def delete_fcm_token(user_id: str = Depends(get_current_user)):
    user = firestore_db.collection("users").document(user_id)
    user.update({"fcm_token": None})
    return {"detail": "Token deleted successfully"}
