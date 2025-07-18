# registration.py
import json
import asyncio
import firebase_admin
import requests

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import Depends, File, Form, HTTPException, UploadFile, Query
from firebase_admin import auth

from ..ranking.utils import strip_first_numbers
from ..Season_Pass.Quetes.utils import *
from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        pb_auth, storage_client)
from ..ClimbingLocation.models import ClimbingLocationResp

from .deps import get_current_user
from .utils import create_access_token, create_refresh_token
from .models import UserPatchResp, UserResp, VideoResp, UserRespExtended


# REGISTRATION
@app.post("/api/v1/register/")
def register_user(
    email: str = Form(...), password: str = Form(...), password2: str = Form(...), username: str = Form(...), climbingLocation_id: str = Form(None)
):
    # Generate confirmation code
    # auth.generate_email_verification_link(email)
    try:
        if password != password2:
            raise HTTPException(400, {"password": "Passwords must match"})
        user = pb_auth.create_user_with_email_and_password(email=email, password=password)
        # user = pb_auth.create_user_with_email_and_password(email=email, password=password)

        # Generate validation email
        # pb_auth.send_email_verification(user["idToken"])
        # send_mail("Active ton compte !", "rentre le code suivant dans l'application pour finaliser ton inscription : " + str(link), settings.EMAIL_HOST_USER, [email], fail_silently=False)

        # Add user to Firestore
        # if climbingLocation_id:
        #     climbingLocation_id = firestore_db.collection("climbingLocations").document(climbingLocation_id)

        # générate QR CODE
        # qr = segno.make(user['localId'])
        # #augmente la taille du qr code
        # svg = qr.svg_inline()
        # #add xml style to the svg
        # svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')

        # # Get the contents of the profile image
        # # Upload the image bytes to the blob

        # # Add XML style to the SVG

        # # Get the contents of the profile image
        # blob = storage_client.bucket(BUCKET_NAME).blob(f"user/{user['localId']}/qrcode.svg")
        # # Upload the image bytes to the blob
        # blob.upload_from_string(svg, content_type="image/svg+xml")

        firestore_db.collection("users").document(user["localId"]).set(
            {
                "username": username,
                "email": email,
                "isGym": False,
                # 'qrcode': blob.public_url,
            }
        )
        # Send confirmation code to user (e.g., via email or SMS)
        # _send_confirmation_email(email, confirmation_code)

        return {"message": "User registered successfully. Please check your email for confirmation code."}
    except requests.exceptions.HTTPError as e:
        error_json = json.loads(e.args[1])
        error = error_json["error"]["message"]
        if error == "EMAIL_EXISTS":
            raise HTTPException(400, {"email": "Cette adresse email est déjà utilisée"})
        if error == "WEAK_PASSWORD : Password should be at least 6 characters":
            raise HTTPException(400, {"password": "Le mot de passe doit contenir au moins 6 caractères"})
        else:
            raise HTTPException(400, {"email": "Une erreur est survenue, veuillez réessayer plus tard"})


@app.post("/api/v1/signin-google/")
def signin_google(uid: str = Form(...), displayName: str = Form(None), email: str = Form(None), photoURL: str = Form(None)):
    try:
        # check if user with that uid exist in db
        user = firestore_db.collection("users").document(uid).get()
        if user.exists:
            print("user exists")
            user = user.to_dict()
            # Create a JWT token to authenticate the user
            access_token = create_access_token(uid)
            refresh_token = create_refresh_token(uid)

            # add those tokens to the user
            firestore_db.collection("users").document(uid).update(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )

            return {
                "access_token": access_token,
                "climbingLocation": user["climbingLocation_id"].id if "climbingLocation_id" in user else None,
                "refresh_token": refresh_token,
                "profile_image_url": user["profile_image_url"] if "profile_image_url" in user else photoURL,
                "userId": uid,
                "name": user["username"] if "username" in user else displayName if displayName else email.split("@")[0],
                "isGym": user["isGym"] if "isGym" in user else False,
            }
        else:
            # print('user does not exist')
            # # Add user to Firestore
            #   #générate QR CODE
            # qr = segno.make(user['localId'])
            # #augmente la taille du qr code
            # svg = qr.svg_inline()
            # #add xml style to the svg
            # svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')

            # # Get the contents of the profile image
            # # Upload the image bytes to the blob

            # # Add XML style to the SVG

            # # Get the contents of the profile image
            # blob = storage_client.bucket(BUCKET_NAME).blob(f"user/{user['localId']}/qrcode.svg")
            # # Upload the image bytes to the blob
            # blob.upload_from_string(svg, content_type="image/svg+xml")

            firestore_db.collection("users").document(uid).set(
                {
                    "username": displayName if displayName else email.split("@")[0],
                    "email": email,
                    "isGym": False,
                    "profile_image_url": photoURL,
                    # 'qrcode': blob.public_url,
                }
            )

            access_token = create_access_token(uid)
            refresh_token = create_refresh_token(uid)

            # add those tokens to the user
            firestore_db.collection("users").document(uid).update(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )
            return {
                "access_token": access_token,
                # "qrcode" : public_url,
                "refresh_token": refresh_token,
                "profile_image_url": photoURL,
                "userId": uid,
                "name": displayName if displayName else email.split("@")[0],
                "isGym": False,
            }

    except requests.exceptions.HTTPError as e:
        error_json = json.loads(e.args[1])
        error = error_json["error"]["message"]
        if error == "EMAIL_EXISTS":
            raise HTTPException(400, {"email": "Cette adresse email est déjà utilisée"})
        if error == "WEAK_PASSWORD : Password should be at least 6 characters":
            raise HTTPException(400, {"password": "Le mot de passe doit contenir au moins 6 caractères"})
        else:
            raise HTTPException(400, {"email": "Une erreur est survenue, veuillez réessayer plus tard"})


@app.post("/api/v1/signin-apple/")
def signin_apple(uid: str = Form(...), displayName: str = Form(None), email: str = Form(None), photoURL: str = Form(None)):
    try:
        # check if user with that uid exist in db
        user = firestore_db.collection("users").document(uid).get()
        if user.exists:
            print("user exists")
            user = user.to_dict()
            # Create a JWT token to authenticate the user
            access_token = create_access_token(uid)
            refresh_token = create_refresh_token(uid)

            # add those tokens to the user
            firestore_db.collection("users").document(uid).update(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )

            return {
                "access_token": access_token,
                "climbingLocation": user["climbingLocation_id"].id if "climbingLocation_id" in user else None,
                "refresh_token": refresh_token,
                "profile_image_url": user["profile_image_url"] if "profile_image_url" in user else photoURL,
                "userId": uid,
                "name": user["username"] if "username" in user else displayName,
                "isGym": user["isGym"] if "isGym" in user else False,
            }
        else:
            print("user does not exist")
            # Add user to Firestore
            if displayName == None:

                userList = list(firestore_db.collection("users").stream())
                lenUSer = len(userList)
                displayName = "user_" + str(lenUSer)
            # générate QR CODE
            # qr = segno.make(user['localId'])
            # #augmente la taille du qr code
            # svg = qr.svg_inline()
            # #add xml style to the svg
            # svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')

            # # Get the contents of the profile image
            # # Upload the image bytes to the blob

            # # Add XML style to the SVG

            # # Get the contents of the profile image
            # blob = storage_client.bucket(BUCKET_NAME).blob(f"user/{user['localId']}/qrcode.svg")
            # # Upload the image bytes to the blob
            # blob.upload_from_string(svg, content_type="image/svg+xml")

            firestore_db.collection("users").document(uid).set(
                {
                    "username": displayName,
                    "email": email,
                    "isGym": False,
                    "profile_image_url": photoURL,
                    # 'qrcode': blob.public_url,
                }
            )
            access_token = create_access_token(uid)
            refresh_token = create_refresh_token(uid)

            # add those tokens to the user
            firestore_db.collection("users").document(uid).update(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "profile_image_url": photoURL,
                "userId": uid,
                "name": displayName,
                "isGym": False,
            }

    except requests.exceptions.HTTPError as e:
        error_json = json.loads(e.args[1])
        error = error_json["error"]["message"]
        if error == "EMAIL_EXISTS":
            raise HTTPException(400, {"email": "Cette adresse email est déjà utilisée"})
        if error == "WEAK_PASSWORD : Password should be at least 6 characters":
            raise HTTPException(400, {"password": "Le mot de passe doit contenir au moins 6 caractères"})
        else:
            raise HTTPException(400, {"email": "Une erreur est survenue, veuillez réessayer plus tard"})


@app.post("/api/v1/login/")
def login(email: str = Form(...), password: str = Form(...)):
    # Get a reference to the auth service
    try:
        user = auth.get_user_by_email(email)
        user_auth = pb_auth.sign_in_with_email_and_password(email, password)
        db_user = firestore_db.collection("users").document(user_auth["localId"]).get().to_dict()

        # if (user.email_verified == False and db_user['isGym'] == False):
        #     print('email not verified')
        #     raise HTTPException(400,{"email" : "Veuillez vérifier votre adresse email avant de vous connecter"})

        # Log the user in
        user = pb_auth.sign_in_with_email_and_password(email, password)

        # Create a custom token

        # Create a JWT token to authenticate the user
        access_token = create_access_token(user["localId"])
        refresh_token = create_refresh_token(user["localId"])

        # add those tokens to the user
        firestore_db.collection("users").document(user["localId"]).update(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )
        climbingLocation_id = (
            db_user["climbingLocation_id"].id if "climbingLocation_id" in db_user and db_user["climbingLocation_id"] != None else None
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "profile_image_url": db_user["profile_image_url"] if "profile_image_url" in db_user else "",
            "userId": user["localId"],
            "climbingLocation": climbingLocation_id if climbingLocation_id else None,
            "name": db_user["username"],
            "isGym": db_user["isGym"],
        }

    except requests.exceptions.HTTPError as e:
        error_json = json.loads(e.args[1])
        print(error_json)
        error = error_json["error"]["message"]
        if error == "EMAIL_NOT_FOUND":
            raise HTTPException(400, {"email": "Adresse email inconnue"})
        elif error == "INVALID_LOGIN_CREDENTIALS":
            raise HTTPException(400, {"password": "Mot de passe incorrect"})
        elif error == "TOO_MANY_ATTEMPTS_TRY_LATER":
            raise HTTPException(400, {"email": "Trop de tentatives, réessayez plus tard !", "password": "Trop de tentatives, réessayez plus tard !"})
        else:
            raise HTTPException(400, {"password": "Mot de passe incorrect"})
    except firebase_admin._auth_utils.UserNotFoundError as e:
        print(e)
        raise HTTPException(400, {"email": "Adresse email inconnue"})


@app.post("/api/v1/logout/")
def logout(user_id: str = Depends(get_current_user)):
    if user_id == None:
        raise HTTPException(400, {"error": "User not found"})

    # check if user exists
    user = firestore_db.collection("users").document(user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})

    firestore_db.collection("users").document(user_id).update(
        {
            "access_token": "",
            "refresh_token": "",
        }
    )
    return {"message": "User logged out successfully"}


@app.post("/api/v1/reset_password/")
def reset_password(email: str = Form(...)):
    try:
        pb_auth.send_password_reset_email(email)
        return {"message": "Un email de réinitialisation de mot de passe vous a été envoyé"}

    except requests.exceptions.HTTPError as e:
        return {"message": "Un email de réinitialisation de mot de passe vous a été envoyé"}


# guest
@app.post("/api/v1/guest/")
async def create_guest(
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    age: int = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    postal_code: str = Form(None),
):
    
    doc_dict = {
        "guest": True,
        "first_name": first_name,
        "last_name": last_name,
        "username": f"{first_name} {last_name}",
        "gender": gender,
        "age": age,
    }

    if address:
        doc_dict["address"] = address
    if city:
        doc_dict["city"] = city
    if postal_code:
        doc_dict["postal_code"] = postal_code

    doc = firestore_async_db.collection("users").document()

    # create token
    access_token = create_access_token(doc.id)
    refresh_token = create_refresh_token(doc.id)

    doc_dict["access_token"] = access_token
    doc_dict["refresh_token"] = refresh_token

    await doc.set(doc_dict)
    return {
        "id": doc.id,
        **doc_dict,
    }


# ME

@app.get("/api/v1/user/me-new/")
async def get_profile(uid: dict = Depends(get_current_user)):
    user = firestore_db.collection("users").document(uid).get().to_dict()
    if not user:
        raise HTTPException(400, {"error": "User not found"})

    # list_sentWalls = firestore_db.collection('users').document(uid).collection('sentWalls').stream()
    avatar = None
    baniere = None
    if 'avatar' in user and user['avatar'] != None:
        avatar = user['avatar'].get().to_dict()
        avatar['id'] = user['avatar'].id
    if 'baniere' in user and user['baniere'] != None:
        baniere = user['baniere'].get().to_dict()
        baniere['id'] = user['baniere'].id
    
    trainee = None
    #check if user is a trainee

    return {
        "id": uid,
        "description": user["description"] if "description" in user else "",
        "total_sent_wall": 0,
        "username": user["username"],
        "qrcode": user["qrcode"] if "qrcode" in user else "",
        "isGym": user["isGym"],
        "lastDateNews": user["lastDateNews"] if "lastDateNews" in user else "",
        "profile_image_url": user["profile_image_url"] if "profile_image_url" in user else "",
    }


@app.patch("/api/v1/user/me/", response_model=UserPatchResp)
async def update_user_profile(
    username: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user),
    description: Optional[str] = Form(None),
    climbingLocation_id: Optional[str] = Form(None),
    # Add other user details you want to update
):
    # Update user details in Firestore
    user_ref = firestore_db.collection("users").document(user_id)
    if username:
        user_ref.update({"username": username})

    if description:
        user_ref.update({"description": description})

    if climbingLocation_id:
        user_ref.update({"climbingLocation_id": firestore_db.collection("climbingLocations").document(climbingLocation_id)})

    # If there's a profile image, upload it to Google Cloud Storage
    if profile_image:
        # Get the contents of the profile image
        image_content = await profile_image.read()

        # Create a blob in the specified bucket
        blob = storage_client.bucket(BUCKET_NAME).blob(f"profile_images/{user_id}/{profile_image.filename}")

        # Upload the image to Google Cloud Storage
        blob.upload_from_string(image_content, content_type=profile_image.content_type)

        # Update user profile image URL in Firestore
        image_url = blob.public_url
        user_ref.update({"profile_image_url": image_url})

    user_dict = user_ref.get().to_dict()
    user_dict["id"] = user_id

    if user_dict.get("climbingLocation_id") != None:
        climbingLocation_id = user_dict["climbingLocation_id"].id
        user_dict["climbingLocation_id"] = climbingLocation_id
        user_dict["climbingLocation"] = {"id": climbingLocation_id}
    else:
        user_dict["climbingLocation_id"] = None
        user_dict["climbingLocation"] = {"id": None}

    if user_dict.get("baniere") != None:
        baniere = user_dict["baniere"].get().to_dict()
        baniere["id"] = user_dict["baniere"].id
        user_dict["baniere"] = baniere
        user_dict["baniere"]["isBought"] = True
        user_dict["baniere"]["isEquiped"] = True

    if user_dict.get("avatar") != None:
        avatar = user_dict["avatar"].get().to_dict()
        avatar["id"] = user_dict["avatar"].id
        user_dict["avatar"] = avatar
        user_dict["avatar"]["isBought"] = True
        user_dict["avatar"]["isEquiped"] = True

    return user_dict


@app.delete("/api/v1/user/me/")
async def delete_user_profile(user_id: str = Depends(get_current_user)):
    # Delete user from Firestore
    # user_db = firestore_db.collection('users').document(user_id)
    auth.delete_user(user_id)  # delete user from firebase auth
    # user_db.delete()
    return {"message": "User deleted successfully"}


@app.get("/api/v1/user/me/friends/", response_model=list[UserResp])
async def get_user_friends(user_id: str = Depends(get_current_user)):
    friends = firestore_db.collection("users").document(user_id).collection("friends").stream()
    list_friends = []
    for friend in friends:
        dict_friend = friend.to_dict()
        user_id = dict_friend["user_id"].id
        dict_friend = dict_friend["user_id"].get().to_dict()
        if dict_friend == None:
            continue
        dict_friend["id"] = user_id
        dict_friend["climbingLocation_id"] = None
        list_friends.append(dict_friend)
    return list_friends


@app.get("/api/v1/user/me/climbingGymSent/")
async def get_user_climbingGym(user_id: str = Depends(get_current_user)):
    # get all climbingGym sent by user
    stripped_user_id = strip_first_numbers(user_id)
    gyms = firestore_async_db.collection("ranking").where(f"{stripped_user_id}.points", ">", 0).stream()
    res = []

    async def get_grades(climbingLocation_id):
        grades = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").get()
        grades_list = []
        for grade in grades:
            dict_grade = grade.to_dict()
            dict_grade["id"] = grade.id
            grades_list.append(dict_grade)

        grades_list.sort(key=lambda x: x["vgrade"])
        return grades_list

    async def get_infos(gym):
        gym_id = gym.id
        if gym_id == "global":
            return
        
        climbingLocation = await firestore_async_db.collection("climbingLocations").document(gym_id).get()
        climbingLocation_dict = climbingLocation.to_dict()
        climbingLocation_dict["id"] = gym_id
        climbingLocation_dict["grades"] = await get_grades(gym_id)

        res.append(climbingLocation_dict)

    await asyncio.gather(*[get_infos(gym) async for gym in gyms])
    return res


@app.get("/api/v1/user/me/videos/", response_model=list[VideoResp])
async def get_user_videos(user_id: str = Depends(get_current_user)):
     # walls to migrate
    vidéos = await (
        firestore_async_db.collection("users")
        .document(user_id)
        .collection("sentWalls")
        .where("beta", ">=", "")
        .get()
    )

    res = []
    for vidéo in vidéos:
        dict_vidéo = vidéo.to_dict()
        res.append({"url": dict_vidéo["beta"]})

    #for vsa 

    # videos = user.get('videos') if 'videos' in user.to_dict() else []

    return res


@app.get("/api/v1/user/{user_id2}/videos/", response_model=list[VideoResp])
async def get_user_videos(user_id2 : str , user_id: str = Depends(get_current_user)):
     # walls to migrate

    #check if user exists and is friend with me, if user not friend, return []
    friendStatus_ref = (
        firestore_async_db.collection("users")
        .document(user_id)
        .collection("friends")
        .where("user_id", "==", firestore_db.collection("users").document(user_id2))
        .stream()
    )
    async for friendStatus in friendStatus_ref:
        break
    else:
        return []
    
    
    vidéos = await (
        firestore_async_db.collection("users")
        .document(user_id2)
        .collection("sentWalls")
        .where("beta", ">=", "")
        .get()
    )

    res = []
    for vidéo in vidéos:
        dict_vidéo = vidéo.to_dict()
        res.append({"url": dict_vidéo["beta"]})

    #for vsa 

    # videos = user.get('videos') if 'videos' in user.to_dict() else []

    return res

# USer
from concurrent.futures import ThreadPoolExecutor


@app.get("/api/v1/user/", response_model=UserRespExtended)
async def get_user_by_uid(user_id: str, uid: dict = Depends(get_current_user)):
    user = await firestore_async_db.collection("users").document(user_id).get()
    if not user.exists:
        raise HTTPException(400, {"error": "User not found"})

    user_dict = user.to_dict()
    user_dict["id"] = user.id
    user_dict["climbingLocation_id"] = None


    if user_dict.get("baniere") != None:
        baniere = (await user_dict["baniere"].get()).to_dict()
        baniere["id"] = user_dict["baniere"].id
        user_dict["baniere"] = baniere
        user_dict["baniere"]["isBought"] = True
        user_dict["baniere"]["isEquiped"] = True

    # get friendStatus
    friendStatus_ref = (
        firestore_async_db.collection("users")
        .document(uid)
        .collection("friends")
        .where("user_id", "==", firestore_db.collection("users").document(user_id))
        .stream()
    )
    async for friendStatus in friendStatus_ref:
        user_dict["friendStatus"] = "FRIEND"
        break
    else:
        friendStatus_ref = (
            firestore_async_db.collection("users")
            .document(uid)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(user_id))
            .stream()
        )

        async for friendStatus in friendStatus_ref:
            user_dict["friendStatus"] = friendStatus.to_dict()["status"]
            break
        else:
            user_dict["friendStatus"] = "NOT_FRIEND"

    # add most recent walls done
    sent_walls = firestore_async_db.collection("users").document(user_id).collection("sentWalls").order_by("date", direction=firestore.Query.DESCENDING).limit(50).stream()

    sentWalls = []
    async def get_sentWall(sentWall):
        dict_sentWall = sentWall.to_dict()
        if "wall" not in dict_sentWall:
            return
        wall = await dict_sentWall["wall"].get()
        wall_dict = wall.to_dict()
        if wall.exists:
            # get climbingLocation
            climbingLocation_ref = dict_sentWall["wall"].parent.parent.parent.parent
            climbingLocation_id = climbingLocation_ref.id
            # climbingLocation = await climbingLocation_ref.get()
            # climbingLocation_dict = climbingLocation.to_dict()
            # climbingLocation_dict["id"] = climbingLocation_id

            # get secteur
            secteur_ref = dict_sentWall["wall"].parent.parent
            secteur = await secteur_ref.get()
            secteur_dict = secteur.to_dict()
            res_secteur = {
                "id": secteur.id,
                "label": secteur_dict.get("label", ""),
                "newlabel": secteur_dict.get("newlabel", ""),
                "images": secteur_dict.get("image", []),
            }

            if isinstance(res_secteur["images"], str):
                res_secteur["images"] = [res_secteur["images"]]
            
            # get grade
            grade_ref = wall_dict.get("grade")
            if grade_ref:
                grade = await grade_ref.get()
                if not grade.exists:
                    return

                grade_dict = grade.to_dict()
                grade_dict["id"] = grade.id

            elif wall_dict.get("grade_id"):
                grade = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(wall_dict["grade_id"]).get()
                if not grade.exists:
                    return

                grade_dict = grade.to_dict()
                grade_dict["id"] = grade.id
            else:
                return # skip wall if no grade

            wall_dict["sentWalls"] = []
            wall_dict["grade"] = grade_dict
            # wall_dict["climbingLocation"] = climbingLocation_dict
            wall_dict["secteur"] = res_secteur
            wall_dict["id"] = wall.id

            dict_sentWall["wall"] = wall_dict
            dict_sentWall["id"] = sentWall.id
            sentWalls.append(dict_sentWall)            

    await asyncio.gather(*[get_sentWall(sentWall) async for sentWall in sent_walls])
    user_dict["sentWalls"] = sentWalls
    return user_dict


@app.get("/api/v1/user-new/")
def get_user_by_uid(user_id: str, uid: dict = Depends(get_current_user)):
    user = firestore_db.collection("users").document(user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})
    user["id"] = user_id
    user["climbingLocation_id"] = None

    # get friendStatus
    friendStatus_ref = (
        firestore_db.collection("users")
        .document(uid)
        .collection("friends")
        .where("user_id", "==", firestore_db.collection("users").document(user_id))
        .get()
    )
    if len(friendStatus_ref) == 0:
        friendStatus_ref = (
            firestore_db.collection("users")
            .document(uid)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(user_id))
            .get()
        )
        if len(friendStatus_ref) == 0:
            user["friendStatus"] = "NOT_FRIEND"
        else:
            user["friendStatus"] = friendStatus_ref[0].to_dict()["status"]
    else:
        user["friendStatus"] = "FRIEND"

    # add walls done
    sent_walls = firestore_db.collection("users").document(user_id).collection("sentWalls").stream()
    list_sentWalls = len(list(sent_walls))

    user["total_sent_wall"] = list_sentWalls
    return user


@app.get("/api/v1/user/list-by-name/", response_model=list[UserRespExtended])
async def list_users_by_name(name: str, uid: dict = Depends(get_current_user)):
    users = firestore_async_db.collection("users").where("username", ">=", name).where("username", "<=", name + "\uf8ff").limit(10).stream()
    if users.__anext__ == None:
        raise HTTPException(400, {"error": "User not found"})
    
    async def get_user(user):
        user_id = user.id
        user_dict = user.to_dict()
        user_dict["id"] = user_id
        user_dict["climbingLocation_id"] = None

        if user_dict.get("baniere") != None:
            baniere = (await user_dict["baniere"].get()).to_dict()
            baniere["id"] = user_dict["baniere"].id
            user_dict["baniere"] = baniere
            user_dict["baniere"]["isBought"] = True
            user_dict["baniere"]["isEquiped"] = True

        # get friendStatus
        friendStatus_ref = (
            firestore_async_db.collection("users")
            .document(uid)
            .collection("friends")
            .where("user_id", "==", firestore_db.collection("users").document(user_id))
            .stream()
        )
        async for friendStatus in friendStatus_ref:
            user_dict["friendStatus"] = "FRIEND"
            break
        else:
            friendStatus_ref = (
                firestore_async_db.collection("users")
                .document(uid)
                .collection("friend_request")
                .where("user_id", "==", firestore_db.collection("users").document(user_id))
                .stream()
            )

            async for friendStatus in friendStatus_ref:
                user_dict["friendStatus"] = friendStatus.to_dict()["status"]
                break
            else:
                user_dict["friendStatus"] = "NOT_FRIEND"

        return user_dict
    
    users_list = await asyncio.gather(*[get_user(user) async for user in users])
    return users_list

@app.get("/api/v1/user/get-user-by-cloc/", response_model=list[UserRespExtended])
async def get_user_by_cloc(cloc_id: str, uid: dict = Depends(get_current_user)):

    users = firestore_async_db.collection("users").where("climbingLocation_id", "==", firestore_db.collection("climbingLocations").document(cloc_id)).limit(20).stream()
    if users.__anext__ == None:
        raise HTTPException(400, {"error": "User not found"})
    
    async def get_user(user):
        user_id = user.id
        user_dict = user.to_dict()
        user_dict["id"] = user_id
        user_dict["climbingLocation_id"] = None

        if user_dict.get("baniere") != None:
            baniere = (await user_dict["baniere"].get()).to_dict()
            baniere["id"] = user_dict["baniere"].id
            user_dict["baniere"] = baniere
            user_dict["baniere"]["isBought"] = True
            user_dict["baniere"]["isEquiped"] = True

        # get friendStatus
        friendStatus_ref = (
            firestore_async_db.collection("users")
            .document(uid)
            .collection("friends")
            .where("user_id", "==", firestore_db.collection("users").document(user_id))
            .stream()
        )
        async for friendStatus in friendStatus_ref:
            user_dict["friendStatus"] = "FRIEND"
            break
        else:
            friendStatus_ref = (
                firestore_async_db.collection("users")
                .document(uid)
                .collection("friend_request")
                .where("user_id", "==", firestore_db.collection("users").document(user_id))
                .stream()
            )

            async for friendStatus in friendStatus_ref:
                user_dict["friendStatus"] = friendStatus.to_dict()["status"]
                break
            else:
                user_dict["friendStatus"] = "NOT_FRIEND"

        return user_dict
    
    users_list = await asyncio.gather(*[get_user(user) async for user in users])
    return users_list

@app.get("/api/v1/user/{user_id}/wall/")
async def get_user_wall(user_id: str, climbingLocation_id: str = None, offset: int = 0, limit: int = 10, uid: dict = Depends(get_current_user)):
    sentwalls = firestore_db.collection("users").document(user_id).collection("sentWalls").stream()
    map_sentWalls = {}
    list_sentWalls_stream = list(sentwalls)
    list_sentWalls_stream.sort(key=lambda x: x.to_dict()["date"], reverse=True)
    for sentWall in list_sentWalls_stream:
        dict_sentWall = sentWall.to_dict()
        if dict_sentWall["wall"].get().to_dict() != None:
            dict_sentWall["id"] = sentWall.id
            dict_sentWall["date"] = dict_sentWall["date"].strftime("%Y-%m-%d %H:%M:%S")
            if dict_sentWall["grade"]:
                grade_id = dict_sentWall["grade"].id
                dict_sentWall["grade"] = dict_sentWall["grade"].get().to_dict() if dict_sentWall["grade"] else None
                dict_sentWall["grade"]["id"] = grade_id

            # get climbingLocation
            climbingLocation = dict_sentWall["wall"].parent.parent.parent.parent  # weirdo
            climbingId = climbingLocation.id
            climbingLocation = climbingLocation.get().to_dict()
            climbingLocation["id"] = climbingId

            # get secteur
            secteur_db = dict_sentWall["wall"].parent.parent
            secteur = {
                "id": secteur_db.id,
                "label": secteur_db.get().to_dict()["label"],
                "images": secteur_db.get().to_dict()["image"],
            }

            # get Wall
            wall_id = dict_sentWall["wall"].id
            dict_sentWall["wall"] = dict_sentWall["wall"].get().to_dict() if dict_sentWall["wall"] else None
            dict_sentWall["wall"]["id"] = wall_id
            wall_grade_id = dict_sentWall["wall"]["grade"].id
            dict_sentWall["wall"]["grade"] = dict_sentWall["wall"]["grade"].get().to_dict() if dict_sentWall["wall"]["grade"] else None
            dict_sentWall["wall"]["grade"]["id"] = wall_grade_id
            # find climbingLocation associated to wall
            dict_sentWall["wall"]["climbingLocation"] = climbingLocation
            dict_sentWall["wall"]["secteur"] = secteur

            if climbingId in map_sentWalls:
                map_sentWalls[climbingId].append(dict_sentWall)
            else:
                map_sentWalls[climbingId] = [dict_sentWall]

    # sort by date

    return map_sentWalls[climbingLocation_id][offset : offset + limit]


@app.get("/api/v1/user/{user_id}/climbingGymSent/")
def get_user_wall(user_id: str, uid: dict = Depends(get_current_user)):
    walls = firestore_db.collection("users").document(user_id).collection("sentWalls").stream()
    res = []

    def get_sentWall(sentWall):
        dict_sentWall = sentWall.to_dict()
        # get climbingLocation
        climbingLocation = dict_sentWall["wall"].parent.parent.parent.parent
        climbingId = climbingLocation.id
        climbingLocation = climbingLocation.get().to_dict()
        climbingLocation["id"] = climbingId
        if climbingLocation not in res:
            return climbingLocation

    with ThreadPoolExecutor() as executor:
        results = [executor.submit(get_sentWall, wall) for wall in walls]
        for result in results:
            try:
                result = result.result()
                if result:
                    res.append(result)
            except Exception as e:
                print("----------------------------")
                print(e)

    return res


@app.get("/api/v2/user/climbingGymSent/", response_model=list[ClimbingLocationResp])
async def get_user_clocs(
    clocs_id: str = None,
    uid: dict = Depends(get_current_user)
):
    if not clocs_id:
        # get subscribed topics
        doc = await firestore_async_db.collection("users").document(uid).get(["subscribed_topics"])
        subscribed_topics = doc.to_dict().get("subscribed_topics", {})
        clocs_id = list(subscribed_topics.keys())
        clocs_ref = [firestore_async_db.collection("climbingLocations").document(cloc_id) for cloc_id in clocs_id]
    else:
        clocs_id = clocs_id.split(",")
        clocs_ref = [firestore_async_db.collection("climbingLocations").document(cloc_id) for cloc_id in clocs_id if cloc_id]

    clocs = firestore_async_db.get_all(clocs_ref)

    # get grades
    async def get_grades(cloc_dict):
        grades = await firestore_async_db.collection("climbingLocations").document(cloc_dict["id"]).collection("grades").get()
        grades_list = []
        for grade in grades:
            dict_grade = grade.to_dict()
            dict_grade["id"] = grade.id
            grades_list.append(dict_grade)

        grades_list.sort(key=lambda x: x["vgrade"])
        cloc_dict["grades"] = grades_list
    
    # get sectors
    async def get_sectors(cloc_dict):
        sectors = await firestore_async_db.collection("climbingLocations").document(cloc_dict["id"]).collection("secteurs").get()
        sectors_list = []
        for sector in sectors:
            dict_sector = sector.to_dict()
            dict_sector["id"] = sector.id

            thumbnails = dict_sector.get("thumbnails", [])
            if thumbnails:
                dict_sector["image"] = thumbnails

            dict_sector["images"] = dict_sector.get("image", [])
            sectors_list.append(dict_sector)

        cloc_dict["secteurs"] = sectors_list

    clocs_dict = []
    async for cloc in clocs:
        cloc_dict = cloc.to_dict()
        cloc_dict["id"] = cloc.id
        clocs_dict.append(cloc_dict)

    await asyncio.gather(
        *[get_grades(cloc_dict) for cloc_dict in clocs_dict],
        *[get_sectors(cloc_dict) for cloc_dict in clocs_dict]
    )

    return clocs_dict