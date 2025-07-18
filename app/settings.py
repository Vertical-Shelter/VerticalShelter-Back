# registration.py
import os
from urllib.parse import urlparse

import firebase_admin
import pyrebase
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from firebase_admin import credentials, firestore, firestore_async
from google.cloud import storage, bigquery
from google.oauth2 import service_account
from pydantic import ValidationError

from .configfiles import dev, prod
from .metrics import setup_metrics

# init firebase
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENV_MODE = os.getenv("ENV_MODE", "dev")

dev_cred = os.path.join(BASE_DIR, 'XXXXX')
prod_cred = os.path.join(BASE_DIR, 'XXXXX') # Replace with your production credentials file path
if ENV_MODE == "prod":
    pb_auth = pyrebase.initialize_app(prod.firebaseConfig).auth()
    BUCKET_NAME = prod.BUCKET_NAME
    FIREBASE_CRED = prod_cred
    TABLE_ID = "sentwalls"
else:
    pb_auth = pyrebase.initialize_app(dev.firebaseConfig).auth()
    BUCKET_NAME = dev.BUCKET_NAME
    FIREBASE_CRED = dev_cred
    TABLE_ID = "sentwalls_dev"


PROJECT_ID = "XXXXXX"
DATASET_ID = "statistics"
TABLE_PATH = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
BQ_CRED = service_account.Credentials.from_service_account_file(prod_cred)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = FIREBASE_CRED
firebase_admin.initialize_app(credentials.Certificate(FIREBASE_CRED))
bq_client = bigquery.Client(credentials=BQ_CRED)
storage_client = storage.Client()

firestore_db = firestore.client()
firestore_async_db = firestore_async.client()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add your frontend origin here
    allow_credentials=True,
    allow_methods=["POST", "PUT", "GET", "OPTIONS", "DELETE", "PATCH"],
    allow_headers=["*"],
)

CLOUDRUN_SERVICE_URL = os.getenv("CLOUDRUN_SERVICE_URL")

if CLOUDRUN_SERVICE_URL:
    ALLOWED_HOSTS = [urlparse(CLOUDRUN_SERVICE_URL).netloc]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

setup_metrics(app)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    print(exc.errors(), exc.json())

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.json()}
    )
