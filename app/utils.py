from fastapi import HTTPException, UploadFile

from .settings import BUCKET_NAME, storage_client


async def send_file_to_storage_string(file: UploadFile, path, content_type):
    try:
        file_content = await file.read()
        blob = storage_client.bucket(BUCKET_NAME).blob(path)
        blob.upload_from_string(file_content, content_type=content_type)
        return blob.public_url
    except Exception as e:
        raise HTTPException(500, {"error": "Failed to upload file."})


async def send_file_to_storage(file: UploadFile, path, content_type):
    try:
        blob = storage_client.bucket(BUCKET_NAME).blob(path)
        blob.upload_from_file(file.file, content_type=content_type)
        return blob.public_url
    except Exception as e:
        raise HTTPException(500, {"error": "Failed to upload file."})
