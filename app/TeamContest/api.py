import datetime
import os
import time
from typing import Dict, List, Optional

import pandas as pd
from fastapi import Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException

from ..contest.models import ContestResp
from ..news.utils import handle_notif
from ..qrcode.api import QRCODE_APP_BASE_URL
from ..qrcode.utils import create_custom_qrcode_png
from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        storage_client)
from ..Teams.models import TeamResp
from ..Teams.utils import impersonate_user
from ..User.deps import get_current_user
from ..utils import send_file_to_storage
from .models import (Bloc, ListBloc, ListPhase, ListRole, ListScoring, State,
                     TeamContestResp)
from .utils import dispatch_contest_scoring, filter_teams


@app.post("/api/v2/climbingLocation/{climbingLocation_id}/contest/", response_model=TeamContestResp)
async def create_climbingLocation_contest(
    climbingLocation_id: str,

    title: str = Form(...),
    description: str = Form(...),
    image_url: str = Form(None),
    image: UploadFile = File(None),
    scoringType: str = Form("PPB"),

    date: datetime.datetime = Form(...),
    priceE: int = Form(...),
    priceA: int = Form(...),

    hasFinal: bool = Form(...),
    doShowResults: bool = Form(True),
    rankingNames: List[str] = Form([]),
    pointsPerZone: int = Form(500),

    roles: ListRole = Form([]),
    blocs: ListBloc = Form([]),
    phases: ListPhase = Form([]),
    uid: dict = Depends(get_current_user),

):
    
    blocs_dict = blocs.model_dump()["blocs"]
    phases_dict = phases.model_dump()["phase"]

    # get last if from climbingLocation
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document()
    doc_id = doc_ref.id

    new_doc = {
        "event_id": doc_id,
        "title": title,
        "description": description,
        "image_url": image_url,
        "date": date,
        "priceE": priceE,
        "priceA": priceA,
        "hasFinal": hasFinal,
        "rankingNames": rankingNames,
        "doShowResults": doShowResults,
        "scoringType": scoringType,
        "pointsPerZone": pointsPerZone,
        "roles": roles.roles,
        "blocs": blocs_dict,
        "phases": phases_dict,
        "etat": State.A_VENIR,
        "version": 2,
    }

    if not image_url and image:
        path = f"climbingLocations/{climbingLocation_id}/contest/{doc_ref.id}/{image.filename}"
        image_url = await send_file_to_storage(image, path, image.content_type)
        new_doc["image_url"] = image_url

    # create qrcode
    qrcode_url = f"{QRCODE_APP_BASE_URL}contest_detail?climbingLocationId={climbingLocation_id}&contestId={doc_ref.id}&version=2"
    url = create_custom_qrcode_png(qrcode_url, bucket_url=f"climbingLocations/{climbingLocation_id}/contest/{doc_ref.id}/qrcode.png")
    new_doc["qrCode_url"] = url
    await doc_ref.set(new_doc)

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
    return new_doc


@app.patch("/api/v2/climbingLocation/{climbingLocation_id}/contest/{contest_id}/blocs/", response_model=TeamContestResp)
async def patch_blocs(
    climbingLocation_id: str,
    contest_id: str,
    blocs: ListBloc = Form(...),
    images: List[UploadFile] = File([]),
    uid: str = Depends(get_current_user)
):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    contest = await contest_ref.get()
    contest_dict = contest.to_dict()
    if not contest.exists:
        raise HTTPException(404, detail="Contest not found")
    
    prev_blocs = contest.get("blocs", [])

    for i, bloc in enumerate(blocs.blocs):
        if i < len(prev_blocs):
            prev_blocs[i].update(bloc)
        else:
            prev_blocs.append(dict(bloc))

    # upload images
    for i, image in enumerate(images):
        try: # there might be some issue with the index, so just in case
            bloc_index = int(image.filename.split(".")[0]) - 1 

            path = f"climbingLocations/{climbingLocation_id}/contest/{contest_id}/blocs/{image.filename}"
            image_url = await send_file_to_storage(image, path, image.content_type)
            prev_blocs[bloc_index]["image_url"] = image_url

        except Exception as e:
            print(e)

    await contest_ref.update({"blocs": prev_blocs})

    contest_dict["blocs"] = prev_blocs
    return contest_dict
    

@app.get("/api/v2/climbingLocation/{climbingLocation_id}/contest/", response_model=List[ContestResp | TeamContestResp] | ContestResp | TeamContestResp)
async def get_climbingLocation_contest(
    climbingLocation_id: str,
    contest_id: Optional[str] = None,
    uid: dict = Depends(get_current_user)
):
    if contest_id == None:
        contests = []
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
            if "date" in dict_doc and isinstance(dict_doc["date"], datetime.datetime):
                dict_doc["date"] = dict_doc["date"].strftime("%Y-%m-%d")

            contests.append(dict_doc)

        contests.sort(key=lambda x: x["date"], reverse=True)
        return contests

    contest = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id).get()
    contest_dict = contest.to_dict()
    if not contest.exists:
        raise HTTPException(404, detail="Contest not found")
    contest_dict["id"] = contest.id

    return contest_dict


@app.delete("/api/v2/climbingLocation/{climbingLocation_id}/contest/{contest_id}/")
async def delete_climbingLocation_contest(climbingLocation_id: str, contest_id: str, uid: dict = Depends(get_current_user)):
    doc_ref = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    doc_ref.delete()
    return {"message": "Contest deleted successfully"}


@app.patch("/api/v2/climbingLocation/{climbingLocation_id}/contest/", response_model=TeamContestResp)
@app.put("/api/v2/climbingLocation/{climbingLocation_id}/contest/", response_model=TeamContestResp)
async def modify_climbingLocation_contest(
    climbingLocation_id: str,
    contest_id: str,

    title: str = Form(None),
    description: str = Form(None),
    image_url: str = Form(None),
    image: UploadFile = File(None),
    scoringType: str = Form(None),

    date: str = Form(None),
    priceE: int = Form(None),
    priceA: int = Form(None),

    state : int = Form(None),

    rankingNames: List[str] = Form(None),
    hasFinal: bool = Form(None),
    doShowResults: bool = Form(None),
    roles: ListRole = Form(None),
    blocs: ListBloc = Form(None),
    phases: ListPhase = Form(None),

    uid: dict = Depends(get_current_user),
):

    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    contest = await contest_ref.get()
    contest_dict = contest.to_dict()
    if not contest or not contest.exists:
        raise HTTPException(404, detail="Contest not found")

    to_update = {}
    if title:
        to_update["title"] = title
    if description:
        to_update["description"] = description
    if image_url:
        to_update["image_url"] = image_url
    if rankingNames:
        to_update["rankingNames"] = rankingNames
    if state != None:
        to_update["etat"] = state
    if scoringType:
        to_update["scoringType"] = scoringType
    if date:
        to_update["date"] = date
    if priceE:
        to_update["priceE"] = priceE
    if priceA:
        to_update["priceA"] = priceA
    if hasFinal != None:
        to_update["hasFinal"] = hasFinal
    if doShowResults:
        to_update["doShowResults"] = doShowResults
    if roles:
        to_update["roles"] = roles.roles
    if blocs:
        to_update["blocs"] = blocs.model_dump()["blocs"]
    if phases:
        to_update["phases"] = phases.model_dump()["phase"]

    if not image_url and image:
        path = f"climbingLocations/{climbingLocation_id}/contest/{contest_id}/{image.filename}"
        image_url = await send_file_to_storage(image, path, image.content_type)

    if image_url:
        to_update["image_url"] = image_url
    
    await contest_ref.update(to_update)
    contest_dict.update(to_update)
    contest_dict["id"] = contest.id
    return contest_dict


@app.post("/api/v2/climbingLocation/{climbingLocation_id}/contest/{contest_id}/score/", response_model=dict)
async def score_contest(
    climbingLocation_id: str,
    contest_id: str,
    score: ListScoring = Form(...),
    impersonate_id: str = Form(None),
    uid: dict = Depends(get_current_user),
):
    uid = await impersonate_user(uid, impersonate_id)

    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    user_ref = firestore_async_db.collection("users").document(uid)

    teams = await contest_ref.collection("teams").where(f"members.u_{uid}", "==", user_ref).get()
    if len(list(teams)) == 0:
        raise HTTPException(400, detail="User not found in any team")
    
    team = teams[0]
    team_id = team.id

    # HARDFIX TOREMOVE
    contest_blocs = await contest_ref.get(["blocs"])
    contest_blocs_dict = contest_blocs.to_dict()
    num_blocs = len(contest_blocs_dict.get("blocs", []))
    # fill with 0 if not enough blocs
    if len(score.score) != num_blocs:
        score.score += [0] * (num_blocs - len(score.score))

    # update 
    await contest_ref.update({
        f"score.{team_id}.members.u_{uid}.blocs": score.score
    })

    return {"message": "Score added successfully"}


@app.get("/api/v2/climbingLocation/{climbingLocation_id}/contest/{contest_id}/score/", response_model=List[TeamResp])
async def get_contest_score(
    climbingLocation_id:str,
    contest_id :str,
    filter : Optional[str] = None,
    uid: dict = Depends(get_current_user)
):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    contest_score = await dispatch_contest_scoring(contest_ref, filter)
    sorted_score = sorted(contest_score, key=lambda x: x["points"], reverse=True)

    # HARDFIX TOREMOVE
    contest_blocs = await contest_ref.get(["blocs"])
    contest_blocs_dict = contest_blocs.to_dict()
    num_blocs = len(contest_blocs_dict.get("blocs", []))

    for teams in sorted_score:
        for member in teams.get("members", {}).values():
            member["blocs"] = member.get("blocs", [])
            # fill with 0 if not enough blocs
            if len(member["blocs"]) < num_blocs:
                member["blocs"] += [0] * (num_blocs - len(member["blocs"]))

    return sorted_score


@app.get("/api/v2/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat-download-pdf/")
async def generate_excel(
    climbingLocation_id: str,
    contest_id: str,
    uid: dict = Depends(get_current_user),
):
    contest_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("contest").document(contest_id)
    contest_score = await dispatch_contest_scoring(contest_ref, None)
    sorted_score = sorted(contest_score, key=lambda x: x["points"], reverse=True)

    contest_data = await contest_ref.get(["rankingNames", "blocs"])
    contest_data_dict = contest_data.to_dict()
    ranking_names = contest_data_dict.get("rankingNames", [])
    blocs = contest_data_dict.get("blocs", [])

    FILENAME = f"output_{contest_id}.xlsx"

    with pd.ExcelWriter(FILENAME) as writer:
        for ranking_name in ranking_names:
            filtered_teams = filter_teams(sorted_score, ranking_name)

            for team in filtered_teams:
                bloc_union = [0] * len(blocs)
                for member in team["members"].values():
                    if "blocs" not in member:
                        member["blocs"] = [0] * len(blocs)
                    elif len(member.get("blocs", [])) < len(bloc_union):
                        member["blocs"] += [0] * (len(bloc_union) - len(member["blocs"]))

                    bloc_union = [bloc_union[i] or member["blocs"][i] for i in range(len(bloc_union))]
                team["blocs"] = bloc_union

            data = {
                "Nom": [team["name"] for team in filtered_teams],
                "Score": [int(team["points"]) for team in filtered_teams],
                **{f"Bloc {i+1}": [team["blocs"][i] for team in filtered_teams] for i in range(len(blocs))},
            }

            df = pd.DataFrame(
                data,
            )

            df.index += 1
            df.to_excel(writer, sheet_name=ranking_name)

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
