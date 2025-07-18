import os
import random
from typing import List, Optional

from fastapi import Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from google.cloud import firestore

from ..settings import app, firestore_async_db
from ..User.deps import get_current_user
from ..Teams.models import TeamResp
from .models import VSLBase, VSLResp, LeagueResp
from .utils import (fetch_vsl, fetch_vsls)


@app.get("/api/v1/vsl/information/")
async def get_vsl_information(
    langue: str = "fr",
    edition: int = 1,
    uid=Depends(get_current_user),
):
    #Get the static file from the static folder
    #read each file of folder "static/vsl/edition1/" and store each line in a list as follow : [{html : "line1"}, {html : "line2"}, ...]
    #return the list

    url = f"static/vsl/edition{edition}_{langue}/"
    filePaths = os.listdir(url) 
    vslInformation = []
    for filePath in filePaths:
        _filePath = f"static/vsl/edition1/{filePath}"
        vslInformation.append({"html": FileResponse(_filePath)})
    vslInformation.reverse()
    return vslInformation


@app.post("/api/v1/vsl/", response_model=VSLResp)
async def create_vsl(
    vsl: VSLBase = Form(...),
    uid: str = Depends(get_current_user),
):
    vsl_dict = vsl.model_dump()
    _, ref = await firestore_async_db.collection("vsl").add(vsl_dict)
    # event_id is used for filtering purposes
    await ref.update({"event_id": ref.id})
    return {"id": ref.id, **vsl_dict}


@app.get("/api/v1/vsl/", response_model=VSLResp)
async def get_vsl(
    vsl_id: str = None,
    uid: str = Depends(get_current_user),
):
    # get last active vsl
    if not vsl_id:
        vsls = (
            firestore_async_db.collection("vsl")
            .where("is_actual", "==", True)
            .order_by("end_date", direction=firestore.Query.ASCENDING)
            .limit(1)
            .stream()
        )

        async for vsl in vsls:
            vsl_dict = vsl.to_dict()
            vsl_dict["id"] = vsl.id
            return vsl_dict
        
        raise HTTPException(status_code=404, detail="VSL not found")
    
    # get vsl by id
    vsl = await fetch_vsl(vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="VSL not found")

    return vsl


@app.get("/api/v1/vsls/", response_model=List[VSLResp])
async def list_vsls():
    return await fetch_vsls()


@app.put("/api/v1/vsl/{vsl_id}/", response_model=VSLResp)
async def update_vsl(
    vsl_id: str,
    vsl: VSLBase = Form(...),
    uid: str = Depends(get_current_user),
):
    vsl_dict = vsl.model_dump()

    await firestore_async_db.collection("vsl").document(vsl_id).update(vsl_dict)
    return {"id": vsl_id, **vsl_dict}


@app.post("/api/v1/vsl/{vsl_id}/pre-register/")
async def pre_register(
    vsl_id: str,
    uid=Depends(get_current_user),
):
    vsl_ref = firestore_async_db.collection("vsl").document(vsl_id)

    await vsl_ref.update(
        {f"pre_register.{uid}": True}
    )

    return {"message": "User pre-registered"}


@app.post("/api/v1/vsl/{vsl_id}/leagues/", response_model=LeagueResp)
async def create_league(
    vsl_id: str,
    climbingLocation_id : str = Form(...),
    uid: str = Depends(get_current_user),
):
    league_dict = {
        "climbingLocation_id": climbingLocation_id,
        "vsl_id": vsl_id,
    }

    cloc_id = league_dict["climbingLocation_id"]
    cloc_ref = firestore_async_db.collection("climbingLocations").document(cloc_id)
    cloc = await cloc_ref.get()
    cloc_dict = cloc.to_dict()

    if not cloc.exists:
        raise HTTPException(status_code=404, detail="ClimbingLocation not found")

    # adding cloc information to league
    league_dict.update({
        "name": cloc_dict["name"],
        "city": cloc_dict["city"],
        "image_url": cloc_dict["image_url"],
    })

    vsl_ref = firestore_async_db.collection("vsl").document(vsl_id)
    await vsl_ref.update({"climbingLocations": firestore.ArrayUnion([cloc_id])})

    new_id = league_dict["climbingLocation_id"]
    await firestore_async_db.collection("vsl").document(vsl_id).collection("leagues").document(new_id).set(league_dict)
    return {"id": new_id, **league_dict}


@app.get("/api/v1/vsl/{vsl_id}/leagues/", response_model=List[LeagueResp] | LeagueResp)
async def list_league(
    vsl_id: str,
    leagueId: str = None,
    uid: str = Depends(get_current_user),
):
    if leagueId:
        league = await firestore_async_db.collection("vsl").document(vsl_id).collection("leagues").document(leagueId).get()
        if not league.exists:
            raise HTTPException(status_code=404, detail="League not found")
        return league.to_dict()
    leagues = firestore_async_db.collection("vsl").document(vsl_id).collection("leagues").stream()
    list_leagues = [league.to_dict() async for league in leagues]
    random.shuffle(list_leagues)
    return list_leagues
    

@app.get("/api/v1/vsl/{vsl_id}/leagues/{league_id}/", response_model=List[TeamResp])
async def get_league(
    vsl_id: str,
    league_id: str,
    uid: str = Depends(get_current_user),
):
    league = await firestore_async_db.collection("vsl").document(vsl_id).collection("leagues").document(league_id).get()
    if not league.exists:
        raise HTTPException(status_code=404, detail="League not found")
    
    league_dict = league.to_dict()
    teams = league_dict.get("score", {}).values()
    sorted_teams = sorted(teams, key=lambda x: x.get("points", 0), reverse=True)
    return sorted_teams

