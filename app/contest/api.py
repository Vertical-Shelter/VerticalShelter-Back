import asyncio
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from fastapi import Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException

from ..qrcode.api import QRCODE_APP_BASE_URL
from ..qrcode.utils import create_custom_qrcode_png

from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        storage_client)
from ..news.utils import handle_notif
from ..User.deps import get_current_user
from .models import (ContestInscription, ContestResp,
                     CreateContestResp, InscriptionScoreResp, ListBloc,
                     ListIsBlocSucceed, ListPhase, State,
                     UserInscriptionScoreResp)
from .utils import dispatch_contest_scoring, get_contest, scoring_contest
from ..utils import send_file_to_storage


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/", response_model=CreateContestResp)
async def create_climbingLocation_contest(
    climbingLocation_id: str,
    title: str = Form(...),
    description: str = Form(...),
    date: datetime = Form(...),
    priceE: float = Form(...),
    image: UploadFile = File(None),
    priceA: float = Form(...),
    hasFinal: bool = Form(...),
    doShowResults: bool = Form(True),
    scoringType: str = Form("PPB"),
    pointsPerZone: Optional[int] = Form(500),
    blocs: ListBloc = Form(...),
    phases: ListPhase = Form(...),
    rankingNames: List[str] = Form([]),
    uid: dict = Depends(get_current_user),
    ):

    # get last if from climbingLocation
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document()
    new_doc = {
        "title": title,
        "description": description,
        "image_url": "",
        "date": date,
        "priceE": priceE,
        "priceA": priceA,
        "hasFinal": hasFinal,
        "doShowResults": doShowResults,
        "scoringType": scoringType,
        "pointsPerZone": pointsPerZone,
        "rankingNames": rankingNames,
        "etat": State.A_VENIR,
        "version": 1,
    }

    if image:
        path = f"climbingLocations/{climbingLocation_id}/contest/{doc_ref.id}/{image.filename}"
        image_url = await send_file_to_storage(image, path, image.content_type)
        new_doc["image_url"] = image_url

    # add params to base url
    qrcode_url = f"{QRCODE_APP_BASE_URL}contest_detail?climbingLocationId={climbingLocation_id}&contestId={doc_ref.id}&version=1"

    # create qrcode
    out = create_custom_qrcode_png(qrcode_url, bucket_url=f"climbingLocations/{climbingLocation_id}/contest/{doc_ref.id}/qrcode.png")

    new_doc["qrCode_url"] = out
    await doc_ref.set(new_doc)

    new_doc["blocs"] = []
    new_doc["phases"] = []

    if blocs:
        bloc_col = doc_ref.collection("blocs")
        res = await asyncio.gather(*[bloc_col.add(dict(bloc)) for bloc in blocs.blocs])
        blocs_res = await asyncio.gather(*[r.get() for _, r in res])
        for r in blocs_res:
            bloc_res = r.to_dict()
            bloc_res["id"] = r.id
            new_doc["blocs"].append(bloc_res)

    if phases:
        phase_col = doc_ref.collection("phase")
        res = await asyncio.gather(*[phase_col.add(dict(p)) for p in phases.phase])
        phase_res = await asyncio.gather(*[r.get() for _, r in res])
        for r in phase_res:
            phase_res = r.to_dict()
            phase_res["id"] = r.id
            new_doc["phases"].append(phase_res)

    await handle_notif(
        "NEW_CONTEST",
        [title],
        [description],
        notif_topic=climbingLocation_id,
        image_url=new_doc.get("image_url"),
        climbingLocation_id=climbingLocation_id,
        contest_id=doc_ref.id,
    )

    new_doc["id"] = doc_ref.id
    new_doc["date"] = new_doc["date"].strftime("%Y-%m-%d")
    return new_doc

@app.put("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/start/", response_model=ContestResp)
async def start_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    doc_ref.update({"etat": State.EN_COURS})
    return await get_contest(doc_ref.get(), climbingLocation_id, contest_id, uid)

@app.put("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/end/", response_model=ContestResp)
async def end_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    doc_ref.update({"etat": State.TERMINE})
    return await get_contest(doc_ref.get(), climbingLocation_id, contest_id, uid)

@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/start/", response_model=ContestResp)
async def start_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    doc_ref.update({"etat": State.EN_COURS})
    return await get_contest(doc_ref.get(), climbingLocation_id, contest_id, uid)

@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/end/", response_model=ContestResp)
async def end_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    doc_ref.update({"etat": State.TERMINE})
    return await get_contest(doc_ref.get(), climbingLocation_id, contest_id, uid)

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/", response_model=List[ContestResp] | ContestResp)
async def get_climbingLocation_contest(
    climbingLocation_id: str,
    contest_id: Optional[str] = None,
    uid: dict = Depends(get_current_user)
):
    if contest_id == None:
        contest = []
        docs = (
            firestore_async_db
            .collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("contest")
            .stream()
        )

        async for doc in docs:
            dict_doc = doc.to_dict()
            dict_doc["id"] = doc.id
            
            #format the date to datetime
            if "date" in dict_doc and isinstance(dict_doc["date"], datetime):
                dict_doc["date"] = dict_doc["date"].strftime("%Y-%m-%d")

            # make sure that people with old version cannot see and interact with new contests
            if dict_doc.get("version", 0) <= 1:
                contest.append(dict_doc)

        contest.sort(key=lambda x: x["date"], reverse=True)
        return contest

    doc = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id).get()
    dict_doc = await get_contest(doc, climbingLocation_id, contest_id, uid)
    return dict_doc

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/")
async def delete_climbingLocation_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    try:
        doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
        # delete all inscriptions
        inscriptions = doc_ref.collection("inscription").stream()
        for inscription in inscriptions:
            # delete all bloc in inscription
            blocs = inscription.reference.collection("blocs").stream()
            for bloc in blocs:
                bloc.reference.delete()
            inscription.reference.delete()

        bloc = doc_ref.collection("blocs").stream()
        for b in bloc:
            b.reference.delete()
        for p in doc_ref.collection("phase").stream():
            p.reference.delete()

        doc_ref.delete()
        return {"message": "Contest deleted successfully"}
    except Exception as e:
        raise HTTPException(400, detail=str(e))


@app.put("/api/v1/climbingLocation/{climbingLocation_id}/contest/")
@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/contest/")
async def patch_climbingLocation_contest(
    climbingLocation_id: str,
    contest_id: str,
    title: str = Form(None),
    description: str = Form(None),
    date: Optional[datetime] = Form(None),
    doShowResults: Optional[bool] = Form(None),
    scoreType: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    blocs: ListBloc = Form(None),
    image: Optional[UploadFile] = File(None),
    phases: ListPhase = Form(None),
    rankingNames: List[str] = Form(None),
    uid: dict = Depends(get_current_user),
):

    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    res = doc_ref.get()
    if not res or not res.exists:
        print("Contest not found")
        raise HTTPException(400, detail="Contest not found")

    new_doc = {}
    if image:
        path = f"climbingLocations/{climbingLocation_id}/contest/{doc_ref.id}/{image.filename}"
        image_url = await send_file_to_storage(image, path, image.content_type)
        new_doc["image_url"] = image_url
    if title:
        new_doc["title"] = title
    if description:
        new_doc["description"] = description
    if image:
        new_doc["image_url"] = image_url
    if price:
        new_doc["price"] = price
    if date:
        new_doc["date"] = date
    if doShowResults:
        new_doc["doShowResults"] = doShowResults
    if scoreType:
        new_doc["scoreType"] = scoreType 
    if rankingNames:
        new_doc["rankingNames"] = rankingNames
    if new_doc:
        doc_ref.update(new_doc)
    
    if phases:
        phase_col = doc_ref.collection("phase")
        old_phases = doc_ref.collection("phase").get()

        # compare the old phases with the new ones, update the old ones and add the new ones
        for old_p in old_phases:
            old_p_dict = old_p.to_dict()
            for new_p in phases.phase:
                if old_p_dict.get("numero") == new_p.numero:
                    old_p.reference.update(dict(new_p))
                    break

        for new_p in phases.phase:
            if new_p.numero not in [old_p.to_dict().get("numero") for old_p in old_phases]:
                phase_col.add(dict(new_p))

        # delete if there are phases that are not in the new phases
        for old_p in old_phases:
            old_p_dict = old_p.to_dict()
            if old_p_dict.get("numero") not in [new_p.numero for new_p in phases.phase]:
                old_p.reference.delete()
    
    if blocs:
        blocsStream = doc_ref.collection("blocs").stream()
        for bloc in blocsStream:
            bloc.reference.delete()
        for bloc in blocs.blocs:
            bloc_doc = doc_ref.collection("blocs").document()
            bloc_doc.set(dict(bloc))
        new_doc["blocs"] = [dict(bloc) for bloc in blocs.blocs]
        new_doc["blocs"].sort(key=lambda x: x["numero"])

    new_doc["id"] = doc_ref.id
    return new_doc
 

@app.put("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/inscription/{inscription_id}/", response_model=ContestResp)
async def modif_inscription(
    climbingLocation_id: str,
    contest_id: str,
    inscription_id : str,
    uid: dict = Depends(get_current_user),
    genre : Optional[str] = Form(...),
    nom : Optional[str] = Form(...),
    prenom : Optional[str] = Form(...),
    isMember : Optional[bool] = Form(...),
    phaseId : Optional[str] = Form(...),
    is18YO :  Optional[bool] = Form(...)
):
    contest_ref = firestore_async_db.collection('climbingLocations').document(climbingLocation_id).collection('contest').document(contest_id)
    doc_ref = contest_ref.collection('inscription').document(inscription_id)

    #update the inscription
    await doc_ref.update(
        {
            "genre" : genre,
            "prenom" : prenom,
            "nom" : nom,
            "isMember" : isMember,
            "phaseId" : firestore_db.collection('climbingLocations')
            .document(climbingLocation_id)
            .collection('contest')
            .document(contest_id)
            .collection('phase')
            .document(phaseId),
            "is18YO" : is18YO
        }
    )

    # force refresh
    await contest_ref.update({"last_calculated": time.time(), "num_without_update": 0})
    await dispatch_contest_scoring(contest_ref)

    dict_doc = await get_contest((await contest_ref.get()), climbingLocation_id, contest_id, uid)
    return dict_doc

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/inscription/", response_model=ContestResp)
async def inscription_contest(
    climbingLocation_id: str,
    contest_id: str,
    uid: str = Depends(get_current_user),
    genre: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    isMember: bool = Form(...),
    phaseId: str = Form(...),
    is18YO: bool = Form(...),
):
    contest_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    user_ref = firestore_db.collection("users").document(uid)

    registered = contest_ref.collection("inscription").where("user_ref", "==", user_ref).get()
    if len(list(registered)) > 0:
        return await get_contest(contest_ref.get(), climbingLocation_id, contest_id, uid)

    # Create a new inscription doc with user id 
    inscription_ref = contest_ref.collection("inscription").document(uid)
    inscription_ref.set(
        {
            "user_ref": user_ref,
            "genre": genre,
            "qrCodeScanned": True,
            "prenom": prenom,
            "nom": nom,
            "isMember": isMember,
            "phaseId": contest_ref.collection("phase").document(phaseId),
            "is18YO": is18YO,
        }
    )

    contest_dict = await get_contest(contest_ref.get(), climbingLocation_id, contest_id, uid)

    return contest_dict

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/inscription-guest/")
async def inscription_contest(
    climbingLocation_id: str,
    contest_id: str,
    genre: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    isMember: bool = Form(...),
    phaseId: str = Form(...),
    is18YO: bool = Form(...),
    uid: dict = Depends(get_current_user),
):
    inscription = ContestInscription(isGuest=True, genre=genre, nom=nom, prenom=prenom, isMember=isMember, phaseId=phaseId, is18YO=is18YO)
    contest_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    collection = contest_ref.collection("inscription")
    _, ref = collection.add(
        {
            "user_ref": None,
            "genre": inscription.genre,
            "qrCodeScanned": False,
            "prenom": inscription.prenom,
            "nom": inscription.nom,
            "isMember": inscription.isMember,
            "phaseId": firestore_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("contest")
            .document(contest_id)
            .collection("phase")
            .document(inscription.phaseId),
            "is18YO": inscription.is18YO,
        }
    )

    new_doc = await (
        firestore_async_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("contest")
        .document(contest_id)
        .collection("inscription")
        .document(ref.id).get()
    )
    new_doc_dict = new_doc.to_dict()
    new_doc_dict["id"] = new_doc.id
    new_doc_dict["phaseId"] = None

    return new_doc_dict


@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/inscription/")
async def desinscription_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    contest_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    inscripted = contest_ref.collection("inscription").where("user_ref", "==", firestore_db.collection("users").document(uid)).get()
    if len(list(inscripted)) == 0:
        return {"message": "You are not inscripted to this contest"}
    inscripted[0].reference.delete()
    return {"message": "Inscription deleted successfully"}


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/qrCodeScan/")
async def scanQRCode(climbingLocation_id: str, contest_id, uid: dict = Depends(get_current_user)):
    contest_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    inscripted = contest_ref.collection("inscription").where("user_ref", "==", firestore_db.collection("users").document(uid)).get()
    if len(list(inscripted)) == 0:
        return {"message": "You are not inscripted to this contest"}
    inscripted[0].reference.update({"qrCodeScanned": True})
    return {"message": "QR code scanned successfully"}


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/score/", response_model=dict)
async def score_contest_user(
    climbingLocation_id: str,
    contest_id: str,
    uid: dict = Depends(get_current_user),
    score: ListIsBlocSucceed = Form(...),
):

    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    user_ref = firestore_async_db.collection("users").document(uid)
    matched_ref = await contest_ref.collection("inscription").where("user_ref", "==", user_ref).get()
    if len(list(matched_ref)) == 0:
        print("Inscription not found")
        return {"message": "Inscription not found"}
    inscription = matched_ref[0]

    # # should only score if qr code is scanned
    # if inscription.to_dict().get("qrCodeScanned", False) == False:
    #     return {"message": "QR code not scanned"}

    return await scoring_contest(contest_ref, inscription, score)


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/score-guest/", response_model=dict)
async def score_contest_guest(
    climbingLocation_id: str,
    contest_id: str,
    inscription_id: str = Form(...),
    uid: dict = Depends(get_current_user),
    score: ListIsBlocSucceed = Form(...),
):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    inscription_ref = contest_ref.collection("inscription").document(inscription_id)
    inscription = await inscription_ref.get()
    if not inscription.exists:
        return {"message": "Inscription not found"}
    
    return await scoring_contest(contest_ref, inscription, score)


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat/", response_model=List[InscriptionScoreResp | UserInscriptionScoreResp])
async def get_contest_score_gym(
    climbingLocation_id:str,
    contest_id :str,
    filter : Optional[str] = None,
    uid: dict = Depends(get_current_user)
):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    isGym = (await firestore_async_db.collection("users").document(uid).get(["isGym"]))
    isGym = False if not isGym.exists else isGym.to_dict().get("isGym", False)

    if not filter:
        filter = "global"

    if isGym:
        # force refresh
        await contest_ref.update({"last_calculated": time.time(), "num_without_update": 0})
        contest_dict = await dispatch_contest_scoring(contest_ref)

        if filter == "J":
            return [insc for insc in contest_dict.get("global", []) if not insc.get("is18YO", True)]
        else:
            return contest_dict.get(filter, [])

    else:
        # smart refresh
        infos = (await contest_ref.get(["num_without_update", "last_calculated", "doShowResults"])).to_dict()
        if not infos.get("doShowResults", True):
            return []

        num_without_update = infos.get("num_without_update", 0)
        last_calculated = infos.get("last_calculated", 0)
        contest_dict = {}
        if num_without_update >= 10 or (time.time() - last_calculated) > 60:
            await contest_ref.update({"last_calculated": time.time(), "num_without_update": 0})
            contest_dict = await dispatch_contest_scoring(contest_ref)
        else:
            contest_doc = await contest_ref.get([filter])
            contest_dict = contest_doc.to_dict()

        return [UserInscriptionScoreResp(**inscription) for inscription in contest_dict.get(filter, [])]

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat-user/", response_model=List[UserInscriptionScoreResp])
async def get_contest_score_user(climbingLocation_id:str, contest_id :str, filter : Optional[str] = None, uid: dict = Depends(get_current_user)):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)

    infos = (await contest_ref.get(["num_without_update", "last_calculated", "doShowResults"])).to_dict()
    if not infos.get("doShowResults", True):
        return []

    if not filter:
        filter = "global"

    # smart refresh
    num_without_update = infos.get("num_without_update", 0)
    last_calculated = infos.get("last_calculated", 0)
    contest_dict = {}
    if num_without_update >= 10 or (time.time() - last_calculated) > 60:
        await contest_ref.update({"last_calculated": time.time(), "num_without_update": 0})
        contest_dict = await dispatch_contest_scoring(contest_ref)
    else:
        contest_doc = await contest_ref.get([filter])
        contest_dict = contest_doc.to_dict()

    return contest_dict.get(filter, [])

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat-download-pdf/")
async def generate_excel(
    climbingLocation_id: str,
    contest_id: str,
    uid: dict = Depends(get_current_user),
):
    contest_ref = (
        firestore_async_db
        .collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("contest")
        .document(contest_id)
    )
    # force refresh
    res = await dispatch_contest_scoring(contest_ref)
    res_g = res["global"]
    res_F = res["F"]
    res_M = res["M"]
    res_J = [insc for insc in res_g if not insc.get("is18YO", True)]

    res_g_pn = []
    res_g_score = []
    # res_g_zone = []
    for res in res_g:
        str_res = res["prenom"] + " " + res["nom"]
        res_g_pn.append(str_res)
        res_g_score.append(res["points"])
        # res_g_zone.append(res["nbZone"])

    res_F_pn = []
    res_F_score = []
    # res_F_zone = []
    for res in res_F:
        str_res = res["prenom"] + " " + res["nom"]
        res_F_pn.append(str_res)
        res_F_score.append(res["points"])
        # res_F_zone.append(res["nbZone"])

    res_M_pn = []
    res_M_score = []
    # res_M_zone = []
    for res in res_M:
        str_res = res["prenom"] + " " + res["nom"]
        res_M_pn.append(str_res)
        res_M_score.append(res["points"])
        # res_M_zone.append(res["nbZone"])

    res_J_pn = []
    res_J_score = []
    # res_J_zone = []
    for res in res_J:
        str_res = res["prenom"] + " " + res["nom"]
        res_J_pn.append(str_res)
        res_J_score.append(res["points"])
        # res_J_zone.append(res["nbZone"])

    dfg = pd.DataFrame({"Nom": res_g_pn, "Score": res_g_score})
    dff = pd.DataFrame({"Nom": res_F_pn, "Score": res_F_score})
    dfh = pd.DataFrame({"Nom": res_M_pn, "Score": res_M_score})
    dfj = pd.DataFrame({"Nom": res_J_pn, "Score": res_J_score})

    FILENAME = f"output_{contest_id}.xlsx"
    with pd.ExcelWriter(FILENAME) as writer:
        dfg.to_excel(writer, sheet_name="Global")
        dff.to_excel(writer, sheet_name="Femme")
        dfh.to_excel(writer, sheet_name="Homme")
        dfj.to_excel(writer, sheet_name="Jeune")

    # remove previous file
    blobs = storage_client.list_blobs(BUCKET_NAME, prefix=f"climbingLocations/{climbingLocation_id}/contest/{contest_id}/result_")
    for blob in blobs:
        blob.delete()

    # upload to storage
    blob = storage_client.bucket(BUCKET_NAME).blob(f"climbingLocations/{climbingLocation_id}/contest/{contest_id}/result_{int(time.time())}.xlsx")
    blob.upload_from_filename(FILENAME)
    blob.make_public()

    # remove the file
    os.remove(FILENAME)

    return {"url": blob.public_url}

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat-less18/", response_model=Dict[str, List[InscriptionScoreResp]])
async def get_contest_score_less18(climbingLocation_id: str, contest_id: str, filter: Optional[str] = None, uid: dict = Depends(get_current_user)):

    contest_ref = (
        firestore_async_db
        .collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("contest")
        .document(contest_id)
    )
    # force refresh
    scores = await dispatch_contest_scoring(contest_ref)

    inscriptions = await (
        firestore_async_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("contest")
        .document(contest_id)
        .collection("inscription")
        .where("is18YO", "==", False)
        .get()
    )
    inscriptions_id = [inscription.id for inscription in inscriptions]

    res = {"global": [], "F": [], "M": []}

    for score in scores["global"]:
        if score["id"] in inscriptions_id:
            res["global"].append(score)

    for score in scores["F"]:
        if score["id"] in inscriptions_id:
            res["F"].append(score)

    for score in scores["M"]:
        if score["id"] in inscriptions_id:
            res["M"].append(score)

    return res