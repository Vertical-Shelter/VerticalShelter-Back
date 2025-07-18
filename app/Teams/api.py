"""
This module contains the API endpoints to handle teams for different events.
- VSL path: /api/v1/vsl/{vsl_id}/teams/
- Contest path: /api/v1/contest/{contest_id}/teams/
"""

import datetime
import random
from typing import List

from fastapi import Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from google.cloud import firestore

from ..settings import app, firestore_async_db
from ..User.api import create_guest
from ..User.deps import get_current_user
from ..utils import send_file_to_storage
from ..VSL.utils import migrate_user_history, remove_user_points
from .models import ContestTeamBase, InscriptionParam, TeamBase, TeamResp
from .utils import (dispatch_on_team_delete, dispatch_on_team_update,
                    fetch_team, fetch_teams, fetch_user_team, get_event,
                    get_user, impersonate_user)


@app.post("/api/v1/{event_type}/{event_id}/teams/", response_model=TeamResp, response_model_exclude_none=True)
async def create_team(
    event_type: str,
    event_id: str,
    team: ContestTeamBase | TeamBase = Form(...),
    image: UploadFile = File(None),
    uid: str = Depends(get_current_user),
):
    event = await get_event(event_type, event_id)

    # check if user already has a team
    user_ref = firestore_async_db.collection("users").document(uid)
    teams = await (
        event.reference
        .collection("teams")
        .where(f"members.u_{uid}", "==", user_ref)
        .get()
    )
    if len(teams) > 0:
        raise HTTPException(status_code=400, detail="User already has a team")

    team_dict = team.model_dump()
    climbingLocation_id = team_dict.get("climbingLocation_id")
    user_ref = firestore_async_db.collection("users").document(uid)

    if image:
        team_dict["image_url"] = await send_file_to_storage(image, f"{event_type}/{event_id}/teams/{uid}_{image.filename}", image.content_type)

    team_dict["access_code"] = "".join(random.choices("0123456789", k=4))
    team_dict["owner"] = user_ref
    team_dict["event_id"] = event_id
    team_dict["members"] = {}
    team_dict["points"] = 0

    team_dict_tmp = team_dict.copy()
    team_dict_tmp["created_at"] = datetime.datetime.now()

    _, team_ref = await event.reference.collection("teams").add(team_dict_tmp)
    team_dict["id"] = team_ref.id

    await dispatch_on_team_update(event_type, event.reference, team_ref, team_dict, climbingLocation_id=climbingLocation_id)
    return await fetch_team(event_type, event_id, team_ref.id, uid=uid)


@app.get("/api/v1/{event_type}/{event_id}/teams/", response_model=List[TeamResp], response_model_exclude_none=True)
async def get_teams(
    event_type: str,
    event_id: str,
    climbingLocation_id: str = None, # Optional parameter
    uid: str = Depends(get_current_user),
):
    return await fetch_teams(event_type, event_id, climbingLocation_id=climbingLocation_id)


@app.get("/api/v1/{event_type}/{event_id}/teams/{team_id}/", response_model=TeamResp, response_model_exclude_none=True)
async def get_team(
    event_type: str,
    event_id: str,
    team_id: str,
    uid: str = Depends(get_current_user),
):
    if team_id == "my":
        ret = await fetch_user_team(event_type, event_id, uid)
        if not ret:
            raise HTTPException(status_code=404, detail="Team not found")
        return ret

    return await fetch_team(event_type, event_id, team_id, uid=uid)


@app.patch("/api/v1/{event_type}/{event_id}/teams/{team_id}/", response_model=TeamResp, response_model_exclude_none=True)
async def update_team(
    event_type: str,
    event_id: str,
    team_id: str,
    team: TeamBase,
    image: UploadFile = File(None),
    impersonate_id: str = Form(None),
    uid: str = Depends(get_current_user),
):
    uid = await impersonate_user(uid, impersonate_id)
    event = await get_event(event_type, event_id)
    to_update = team.model_dump()

    team_ref = (
        event.reference
        .collection("teams")
        .document(team_id)
    )

    team = await team_ref.get()
    team_dict = team.to_dict()
    if not team.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    climbingLocation_id = team_dict.get("climbingLocation_id")

    if image:
        to_update["image_url"] = await send_file_to_storage(image, f"{event_type}/{event_id}/teams/{uid}_{image.filename}")

    await team.reference.update(to_update)
    await dispatch_on_team_update(event_type, event.reference, team_ref, to_update, climbingLocation_id=climbingLocation_id)

    return await fetch_team(event_type, event_id, team_id, uid=uid)

@app.patch("/api/v1/{event_type}/{event_id}/teams/{team_id}/role/", response_model=TeamResp, response_model_exclude_none=True)
async def update_role(
    event_type: str,
    event_id: str,
    team_id: str,
    role: str = Form(...),
    user_id: str = Form(None),
    impersonate_id: str = Form(None),
    uid: str = Depends(get_current_user),
):
    uid = await impersonate_user(uid, impersonate_id)
    event = await get_event(event_type, event_id)

    if not user_id:
        user_id = uid

    team_ref: firestore.AsyncCollectionReference = (
        event.reference
        .collection("teams")
        .document(team_id)
    )

    team = await team_ref.get()
    if not team.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    climbingLocation_id = team.to_dict().get("climbingLocation_id")

    await team_ref.update({f"roles.{role}": user_id})
    await dispatch_on_team_update(
        event_type,
        event.reference,
        team_ref,
        {f"roles.{role}": user_id},
        climbingLocation_id=climbingLocation_id
    )
    return await fetch_team(event_type, event_id, team_id, uid=uid)

@app.post("/api/v1/{event_type}/{event_id}/teams/{team_id}/join/", response_model=TeamResp, response_model_exclude_none=True)
async def join_team(
    event_type: str,
    event_id: str,
    team_id: str,
    inscription: InscriptionParam = Form(...),
    uid: str = Depends(get_current_user),
):
    event = await get_event(event_type, event_id)

    team_ref = (
        event.reference
        .collection("teams")
        .document(team_id)
    )

    team = await team_ref.get()
    team_dict = team.to_dict()
    if not team.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    climbingLocation_id = team_dict.get("climbingLocation_id")

    # create user if guest
    inscription_dict = inscription.model_dump()
    if inscription_dict.get("is_guest"):
        uid = (await create_guest(
            first_name=inscription_dict["first_name"],
            last_name=inscription_dict["last_name"],
            gender=inscription_dict["gender"],
            age=inscription_dict["age"],
            address=None,
            city=None,
            postal_code=None,
        ))["id"]

    user_ref = firestore_async_db.collection("users").document(uid)

    # get old_team (if any)
    user = await user_ref.get()
    user_dict = user.to_dict()
    old_team_id = user_dict.get(f"{event_type}.{event_id}.old_team")
    old_team_ref = event.reference.collection("teams").document(old_team_id) if old_team_id else None

    to_update = {
        f"members.u_{uid}": user_ref,
    }

    if len(team_dict.get("members", {})) == 0:
        to_update["owner"] = user_ref

    if inscription_dict.get("role"):
        to_update[f"roles.{inscription_dict['role']}"] = uid 

    await team.reference.update(to_update)
    await user_ref.update(
        {
            f"{event_type}.{event_id}.current_team": team_id,
            f"{event_type}.{event_id}.old_team": None, # remove old team
            "city": inscription_dict["city"],
            "age": inscription_dict["age"],
            "address": inscription_dict["address"],
            "first_name": inscription_dict["first_name"],
            "last_name": inscription_dict["last_name"],
            "postal_code": inscription_dict["postal_code"],
            "gender": inscription_dict['gender'],
            "t_shirt_size": inscription_dict["t_shirt_size"],
        }
    )

    to_update[f"members.u_{uid}"] = await get_user(user_ref)
    to_update[f"members.u_{uid}"]["points"] = 0

    await dispatch_on_team_update(event_type, event.reference, team_ref, to_update, climbingLocation_id=climbingLocation_id)
    await migrate_user_history(event_type, event.reference, climbingLocation_id, user_ref, old_team_ref, team_ref)
    return await fetch_team(event_type, event_id, team_id, uid=uid)


@app.delete("/api/v1/{event_type}/{event_id}/teams/{team_id}/leave/", response_model=TeamResp | None, response_model_exclude_none=True)
async def leave_team(
    event_type: str,
    event_id: str,
    team_id: str,
    impersonate_id: str = Form(None),
    uid: str = Depends(get_current_user),
):
    uid = await impersonate_user(uid, impersonate_id)
    event = await get_event(event_type, event_id)

    team_ref = (
        event.reference
        .collection("teams")
        .document(team_id)
    )

    team = await team_ref.get()
    team_dict = team.to_dict()
    if not team.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    climbingLocation_id = team_dict.get("climbingLocation_id")

    user_ref = firestore_async_db.collection("users").document(uid)
    to_update = {
        f"members.u_{uid}": firestore.DELETE_FIELD,
    }

    # remove role
    for role, role_uid in team_dict.get("roles", {}).items():
        if role_uid == uid:
            to_update[f"roles.{role}"] = firestore.DELETE_FIELD

    await user_ref.update({
        f"{event_type}.{event_id}.current_team": None,
        f"{event_type}.{event_id}.old_team": team_id,
    })

    if team_dict.get("owner").id == uid:
        # transfer ownership to another member
        new_owner = None
        for fmt_member_id in team_dict["members"]:
            # format is u_uuid
            member_id = fmt_member_id.split("u_")[-1]
            if member_id != uid:
                new_owner = team_dict["members"][fmt_member_id]
                break

        # if no other member, delete the team
        if not new_owner:
            await team.reference.delete()
            await dispatch_on_team_delete(
                event_type,
                event.reference,
                team_ref.id,
                climbingLocation_id=climbingLocation_id,
            )
            return None

        to_update["owner"] = new_owner

    await remove_user_points(event_type, event.reference, climbingLocation_id, user_ref, team_ref)
    await team.reference.update(to_update)
    await dispatch_on_team_update(event_type, event.reference, team_ref, to_update, climbingLocation_id=climbingLocation_id)
    return await fetch_team(event_type, event_id, team_id, uid=uid)

@app.put("/api/v1/{event_type}/{event_id}/teams/{team_id}/user/{impersonate_Id}/", response_model=TeamResp, response_model_exclude_none=True)
async def update_user(
    event_type: str,
    event_id: str,
    team_id: str,
    impersonate_Id: str = None,
    inscription: InscriptionParam = Form(...),
    uid: str = Depends(get_current_user),
):
    event = await get_event(event_type, event_id)

    user_ref = firestore_async_db.collection("users").document(impersonate_Id)
    user = await user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")


    inscription_dict = inscription.model_dump()

    await user_ref.update(
        {
            f"{event_type}.{event_id}.current_team": team_id,
            f"{event_type}.{event_id}.old_team": None, # remove old team
            "city": inscription_dict["city"],
            "age": inscription_dict["age"],
            "address": inscription_dict["address"],
            "first_name": inscription_dict["first_name"],
            "last_name": inscription_dict["last_name"],
            "postal_code": inscription_dict["postal_code"],
            "gender": inscription_dict['gender'],
            "t_shirt_size": inscription_dict["t_shirt_size"],
        }
    )

    user = await get_user(user_ref)

    team_ref = (
        event.reference
        .collection("teams")
        .document(team_id)
    )

    team = await team_ref.get()
    team_dict = team.to_dict()
    if not team.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    climbingLocation_id = team_dict.get("climbingLocation_id")

    await team.reference.update({f"members.u_{impersonate_Id}": user_ref})
    await dispatch_on_team_update(event_type, event.reference, team_ref, {f"members.u_{impersonate_Id}": user}, climbingLocation_id=climbingLocation_id)
    return await fetch_team(event_type, event_id, team_id, uid=impersonate_Id)