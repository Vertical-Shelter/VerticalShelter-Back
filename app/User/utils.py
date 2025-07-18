import asyncio
from datetime import datetime, timedelta
from typing import Any, Union

from google.cloud import firestore
from jose import jwt

from ..settings import firestore_db
from .models import UserResp

ACCESS_TOKEN_EXPIRE_MINUTES = 200  # 200 semaines
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = "pokemon"  # should be kept secret
JWT_REFRESH_SECRET_KEY = "pokemon_refresh"  # should be kept secret


def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(weeks=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)
    return encoded_jwt

def getUSer(user_id : str) -> UserResp:
    user = firestore_db.collection("users").document(user_id).get()
    if not user.exists:
        return None
    user = user.to_dict()
    user["id"] = user_id
    if "climbingLocation_id" in user:
        climbingLocation = user["climbingLocation_id"].get().to_dict()
        climbingLocation["id"] = user["climbingLocation_id"].id
        user["climbinbingLocation_id"] = climbingLocation
    return UserResp(**user)
     

async def get_cloc(sentWall_dict):
    climbingLocation = sentWall_dict["wall"].parent.parent.parent.parent
    climbingLocation_dict = (await climbingLocation.get()).to_dict()
    climbingLocation_dict["id"] = climbingLocation.id
    return climbingLocation_dict

async def get_grade(wall_dict):
    if "grade" not in wall_dict:
        return None

    grade_ref = wall_dict["grade"]
    grade_dict = (await grade_ref.get()).to_dict()
    if grade_dict:
        grade_dict["id"] = grade_ref.id
        wall_dict["grade"] = grade_dict
    else:
        return None

    return wall_dict

async def get_secteur(sentWall_dict):
    secteur = sentWall_dict["wall"].parent.parent
    secteur_dict = (await secteur.get()).to_dict()
    secteur_dict["id"] = secteur.id
    return {
        "id": secteur.id,
        "label": secteur_dict.get("label"),
        "images": secteur_dict.get("image"),
        "newlabel": secteur_dict.get("newlabel"),
    }

async def get_sentwall(sentWall: firestore.DocumentSnapshot | firestore.AsyncDocumentReference):
    if isinstance(sentWall, firestore.AsyncDocumentReference):
        sentWall = await sentWall.get()

    sentWall_dict = sentWall.to_dict()
    wall_ref = sentWall_dict.get("wall")
    if not wall_ref:
        return None

    wall = await wall_ref.get()
    wall_dict = wall.to_dict()

    sentWall_dict["id"] = sentWall.id
    sentWall_dict["date"] = sentWall_dict["date"].strftime("%Y-%m-%d %H:%M:%S")

    if not wall.exists or not wall_dict:
        return None
    wall_dict["id"] = wall.id

    # TODO: see if this is really useful
    climbingLocation_dict, secteur_dict, wall_dict = await asyncio.gather(
        get_cloc(sentWall_dict),
        get_secteur(sentWall_dict),
        get_grade(wall_dict)
    )

    if wall_dict is None:
        return None # No grade, no chocolate

    wall_dict["climbingLocation"] = climbingLocation_dict
    wall_dict["secteur"] = secteur_dict
    wall_dict["sentWalls"] = []
    wall_dict["routesettername"] = ""
    wall_dict.pop("routesetter", None)

    sentWall_dict["wall"] = wall_dict
    sentWall_dict["grade"] = None

    return sentWall_dict


def filter_sentWall_with_climbingLocation(sentWalls, climbingLocation_id):
    def filter_cloc(sentwall_ref):
        return sentwall_ref.to_dict()["wall"].parent.parent.parent.parent.id == climbingLocation_id
    return list(filter(filter_cloc, sentWalls))


async def get_user_mini(user_ref):
    if not user_ref:
        return None

    user = await user_ref.get()
    user_dict = user.to_dict()

    return {
        "id": user.id,
        "username": user_dict.get("username"),
        "profile_image_url": user_dict.get("profile_image_url")
    }

async def get_user_teams(user_ref, event_type=None, event_id=None):
    if not user_ref:
        return None

    user = await user_ref.get()
    user_dict = user.to_dict()

    resp = {
        "id": user.id,
        "username": user_dict.get("username"),
        "first_name": user_dict.get("first_name"),
        "last_name": user_dict.get("last_name"),
        "profile_image_url": user_dict.get("profile_image_url"),
        "gender": user_dict.get("gender"),
        "age": user_dict.get("age"),
    }

    if event_type and event_id:
        resp["isSubscribed"] = user_dict.get(event_type, {}).get(event_id, {}).get('isSubscribed', False)

    return resp