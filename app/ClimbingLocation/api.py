from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, UploadFile, status
from fastapi.exceptions import HTTPException
from firebase_admin import messaging
from google.cloud import firestore

from ..news.utils import handle_notif
from ..qrcode.utils import create_custom_qrcode_png
from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        storage_client)
from ..User.deps import get_current_user, get_current_user_optional
from ..utils import send_file_to_storage
from ..Wall.api import liste_attributes
from .models import ClimbingLocation, ClimbingLocationResp, Grade, SecteurResp

QRCODE_APP_BASE_URL = "XXX_APP_BASE_URL"  # Replace with your actual app base URL

# CLOC
@app.post("/api/v1/climbingLocation/", response_model=ClimbingLocationResp)
async def create_climbingLocation(
    name: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    country: str = Form(...),
    isPartnership: bool = Form(True),
    hidden: bool = Form(False),
    topo: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    uid: dict = Depends(get_current_user),
):
    # get last id from climbingLocation
    doc_ref = firestore_db.collection("climbingLocations").document()

    image_url = ""
    topo_url = ""

    if image:
        # Get the contents of the profile image
        image_content = await image.read()

        # Create a blob in the specified bucket
        blob = storage_client.bucket(BUCKET_NAME).blob(f"climbingLocations/{doc_ref.id}/{image.filename}")

        # Upload the image to Google Cloud Storage
        blob.upload_from_string(image_content, content_type=image.content_type)

        # Update user profile image URL in Firestore
        image_url = blob.public_url

    if topo:
        # Get the contents of the profile image
        image_content = await topo.read()

        # Create a blob in the specified bucket
        blob = storage_client.bucket(BUCKET_NAME).blob(f"topos/{doc_ref.id}/{topo.filename}")

        # Upload the image to Google Cloud Storage
        blob.upload_from_string(image_content, content_type=topo.content_type)

        # Update user profile image URL in Firestore
        topo_url = blob.public_url

    cloc = {
        "name": name,
        "address": address,
        "city": city,
        "country": country,
        "image_url": image_url,
        "new_topo_url": topo_url,
        "isPartnership": isPartnership,
        "hidden": hidden,
    }

    doc_ref.set(cloc)
    cloc["id"] = doc_ref.id
    return cloc

@app.get("/api/v1/climbingLocation/", response_model=ClimbingLocationResp)
async def get_climbingLocation_by_id(climbingLocation_id: str, uid: dict = Depends(get_current_user)):
    if not climbingLocation_id or climbingLocation_id == "":
        raise HTTPException(400, {"error": "ClimbingLocation id is required"})

    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    climbingLocation = await doc_ref.get()
    if not climbingLocation.exists:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    climbingLocation = climbingLocation.to_dict()
    climbingLocation["id"] = climbingLocation_id

    # get grades
    grades = doc_ref.collection("grades").stream()
    climbingLocation["grades"] = []
    async for grade in grades:
        dict_grade = grade.to_dict()
        dict_grade["id"] = grade.id
        climbingLocation["grades"].append(dict_grade)

    # sort grades by vgrade
    climbingLocation["grades"].sort(key=lambda x: x["vgrade"])

    # get secteurs
    secteurs = doc_ref.collection("secteurs").stream()
    climbingLocation["secteurs"] = []
    async for secteur in secteurs:
        dict_secteur = secteur.to_dict()
        dict_secteur["id"] = secteur.id
        if "qrCode" not in dict_secteur and "newlabel" in dict_secteur:
            out = create_custom_qrcode_png(QRCODE_APP_BASE_URL + f"vt_main_page?climbingLocationId={climbingLocation_id}&secteurName={dict_secteur['newlabel']}", bucket_url=f"climbingLocations/{climbingLocation_id}/{dict_secteur['newlabel']}.png")
            dict_secteur["qrCode"] = out
            await doc_ref.collection("secteurs").document(secteur.id).update({"qrCode": out})
        climbingLocation["secteurs"].append(dict_secteur)

    # # check si il y a un contest en cours donc etat = 0
    contests = doc_ref.collection("contest").where("etat", "==", 0).limit(1).stream()
    async for contest in contests:
        climbingLocation["actual_contest"] = contest.to_dict()
        climbingLocation["actual_contest"]["id"] = contest.id

    attributes: list[str] = climbingLocation.get("attributes")
    if not attributes:
        attributes = liste_attributes
        await doc_ref.update({"attributes": attributes})

    attributes.sort(key=lambda x: x.lower())
    climbingLocation["attributes"] = attributes

    return climbingLocation

@app.get("/api/v1/climbingLocation/list-by-name/", response_model=List[ClimbingLocationResp])
async def list_climbingLocation(
    name: str = None,
    uid: str = Depends(get_current_user_optional)
):
    if uid:
        user = await firestore_async_db.collection("users").document(uid).get(["roles"])
        user_dict = user.to_dict()
        roles = user_dict.get("roles") if user_dict else []
    else:
        roles = []
    
    query = firestore_async_db.collection("climbingLocations")

    if ("AMBASSADEUR" not in roles) and ("ADMIN" not in roles):
        query = query.where("hidden", "==", False)

    cloc_list = []
    async for cloc in query.stream():
        cloc_dict = cloc.to_dict()
        cloc_dict["id"] = cloc.id
        cloc_list.append(cloc_dict)

    cloc_list.sort(key=lambda x: x["name"].lower())
    return cloc_list
    


@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/", response_model=ClimbingLocationResp)
async def partial_update_cloc(
    climbingLocation_id: str,
    uid: dict = Depends(get_current_user),
    nextClosedSector: int = Form(None),
    newNextClosedSector: str = Form(None),
    image: Optional[UploadFile] = File(None),
    topo: Optional[UploadFile] = File(None),
    ouvreurNames: List[str] = Form(None),
    attributes: List[str] = Form(None),
    holds_color: List[str] = Form(None),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})
    data = {}
    if image:
        data["image_url"] = await send_file_to_storage(image, f"climbingLocations/{climbingLocation_id}/{image.filename}", image.content_type)

    if topo:
        data["topo_url"] = await send_file_to_storage(topo, f"topos/{climbingLocation_id}/{topo.filename}", topo.content_type)

    if nextClosedSector:
        data["nextClosedSector"] = nextClosedSector

    if ouvreurNames:
        data["ouvreurNames"] = ouvreurNames

    if attributes:
        data["attributes"] = attributes

    if holds_color:
        data["holds_color"] = holds_color

    if newNextClosedSector:
        list_newNextClosedSector = newNextClosedSector.split("|")
        data["listNextSector"] = list_newNextClosedSector

        data["newNextClosedSector"] = list_newNextClosedSector[0]
        # get new sector
        secteur = climbingLocation["listNewLabel"]
        listUpdated: list = climbingLocation["listUpdated"]
        for _secteur in climbingLocation["listNewLabel"]:
            if _secteur in data["listNextSector"]:
                # remove from list Update index of secteur
                listUpdated.pop(secteur.index(_secteur))
                secteur.remove(_secteur)

        data["listNewLabel"] = secteur
        data["listUpdated"] = listUpdated

        # send notification to users of the gym about closing sector
        if len(data.get("listNextSector", [])) > 0:
            await handle_notif(
                "SOON_SECT",
                [f"{climbingLocation["name"]} {climbingLocation["city"]} - "],
                [", ".join(data["listNextSector"])],
                notif_topic=climbingLocation_id,
                climbingLocation_id=climbingLocation_id,
            )

    if data == {}:
        raise HTTPException(400, {"error": "No data to update"})

    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id)
    doc_ref.update(data)
    climbingLocation = doc_ref.get().to_dict()
    climbingLocation["id"] = climbingLocation_id
    return climbingLocation


# GRADES
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/add-grade/", response_model=ClimbingLocationResp)
def add_grade_to_cloc(
    uid: dict = Depends(get_current_user),
    climbingLocation_id: str = None,
    grade: List[Grade] = None,
):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id)

    if not doc_ref.get().exists:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # if there are already grades, raise an error
    grades = list(doc_ref.collection("grades").stream())
    if len(grades) > 0:
        raise HTTPException(400, {"error": "ClimbingLocation already has grades, patch it instead"})

    for grade in grade:
        ref2 = grade.ref2 if grade.ref2 else None

        doc_ref.collection("grades").document().set(
            {
                "ref1": grade.ref1,
                "ref2": ref2,
                "vgrade": grade.vgrade,
            }
        )

    cloc_dict = doc_ref.get().to_dict()
    cloc_dict["id"] = climbingLocation_id
    return cloc_dict


@app.post("/api/v1/demande-climbingLocation/")
async def ask_climbingLocation(name: str = Form(...), uid: dict = Depends(get_current_user), city: str = Form(...), instagram: str = Form(None)):
    try:
        # get last if from climbingLocation

        doc_ref = firestore_db.collection("demandeClimbingLocations").document()

        doc_ref.set(
            {
                "name": name,
                "city": city,
                "instagram": instagram,
            }
        )

        return {"message": "ClimbingLocation created successfully"}
    except HTTPException as e:

        raise HTTPException(400, {"error": e})
    except Exception as e:
        raise HTTPException(400,{"error" : e})
    

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/scanQrCode/")
async def scan_qr_code(climbingLocation_id: str, uid: dict = Depends(get_current_user)):
    #get the cloc and check if it official or not
    climbingLocation = firestore_db.collection('climbingLocations').document(climbingLocation_id).get().to_dict()
    if (climbingLocation == None):
        raise HTTPException(400,{"error" : "ClimbingLocation not found"})
    if 'isPartnership' not in climbingLocation or not climbingLocation['isPartnership']:
        raise HTTPException(400,{"error" : "ClimbingLocation is not official"})
    
    #check if the user has the season pass
    season_pass = firestore_db.collection('season_pass').where('is_active', '==', True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict['id'] = id
        season_pass_list.append(season_pass_dict)
    
    if len(season_pass_list) == 0:
        raise HTTPException(status_code=404, detail="Season pass not found")
    
    season_pass = season_pass_list[0]
    #get the user season pass
    user_season_pass_ref = firestore_db.collection('users').document(uid).collection('season_pass').document(season_pass['id'])
    if not user_season_pass_ref.get().exists:
        #the user has not the season pass
        raise HTTPException(status_code=404, detail="User has not the season pass")
    else:
        print("user has the season pass")
    
    #get the user quete
    user_ref = firestore_db.collection('users').document(uid['uid']).collection('season_pass').document(season_pass['id']).collection('quetes_quotidienne')
    user_quete = user_ref.where('name', '==', "QR CODE").stream()
    user_quete = list(user_quete)
    if len(user_quete) == 0:
        raise HTTPException(status_code=404, detail="Quete not found")
    quete_id = user_quete[0].id
    user_quete = user_quete[0].to_dict()
    season_pass_quete = user_quete['quete_ref'].get().to_dict()
     
    if 'is_claimed' in user_quete and  user_quete['is_claimed']:
        raise HTTPException(status_code=404, detail="Quete already claimed")
    
    if user_quete['quota'] >= season_pass_quete['quota']:
        raise HTTPException(status_code=404, detail="Quete already completed")
   
    #increment the quete
    user_ref.document(quete_id).update(
        {
            "quota": firestore.Increment(1)
        }
    )
    
    return {"message" : "Quete updated successfully"}
