from ..settings import firestore_db,   storage_client, BUCKET_NAME, app
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from ..User.deps import get_current_user
from concurrent.futures import ThreadPoolExecutor
from google.cloud import firestore

@app.get("/api/v1/version-apple/")
async def get_version_apple():
    last_version = firestore_db.collection("apple_version").order_by("version", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in last_version:
        return doc.to_dict()
    
@app.get("/api/v1/version-android/")
async def get_version_android():
    last_version = firestore_db.collection("android_version").order_by("version", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in last_version:
        return doc.to_dict()

@app.post("/api/v1/version-apple/")
async def add_version_apple(version: str = Form(...), force_update: bool= Form(...), message: str= Form(...), url: str= Form(...)):
    
    data = {
        "version": version,
        "force_update": force_update,
        "message": message,
        "url": url
    }
    firestore_db.collection("apple_version").add(data)
    return data
    
@app.post("/api/v1/version-android/")
async def add_version_android(version: str = Form(...), force_update: bool = Form(...), message: str = Form(...), url: str = Form(...)):
    
    data = {
        "version": version,
        "force_update": force_update,
        "message": message,
        "url": url
    }
    firestore_db.collection("android_version").add(data)
    return data
