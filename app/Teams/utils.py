import asyncio
import logging

from fastapi import HTTPException
from google.cloud import firestore

from ..settings import firestore_async_db
from ..User.utils import get_user_teams as get_user, get_sentwall
from .models import TeamResp


async def fetch_team(event_type: str, event_id: str, team_id: str, uid: str = None) -> TeamResp:
    event = await get_event(event_type, event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_type} {event_id} not found")
    
    team = await (
        event.reference
        .collection("teams")
        .document(team_id)
        .get()
    )
    if not team.exists:
        return None
    team_dict = team.to_dict()
    team_dict["id"] = team_id
    team_dict["event_id"] = event.id
    team_dict["is_owner"] = team_dict["owner"].id == uid

    members_ref = list(team_dict.get("members", {}).values())
    team_dict["members"] = await asyncio.gather(*[get_user(member) for member in members_ref])

    return team_dict


async def fetch_teams(event_type: str, event_id: str, climbingLocation_id: str = None, uid: str = None, simple=False) -> list[TeamResp]:
    event = await get_event(event_type, event_id)
    if not event:
        return []

    if climbingLocation_id:
        teams = (
            event.reference
            .collection("teams")
            .where("climbingLocation_id", "==", climbingLocation_id)
            .stream()
        )
    else:
        teams = (
            event.reference
            .collection("teams")
            .stream()
        )

    async def get_team(team):
        team_id = team.id
        team_dict = team.to_dict()
        team_dict["id"] = team_id
        team_dict["event_id"] = event.id
        team_dict["is_owner"] = team_dict["owner"].id == uid

        if not simple:
            team_dict["members"] = await asyncio.gather(*[get_user(member) for member in team_dict.get("members", {}).values()])
        return team_dict
    
    return await asyncio.gather(*[get_team(team) async for team in teams])


async def fetch_user_team(event_type: str, event_id: str, user_id: str) -> TeamResp:
    event = await get_event(event_type, event_id)
    if not event:
        return None

    teams = await (
        event.reference
        .collection("teams")
        .where(
            f"members.u_{user_id}",
            "==",
            firestore_async_db.collection("users").document(user_id)
        )
        .limit(1)
        .get()
    )

    if not teams:
        return None

    team = teams[0]
    team_dict = team.to_dict()

    if event_type == "vsl":
        score_team = await event.reference.collection("leagues").document(team_dict["climbingLocation_id"]).get(["score"])
        team_dict = score_team.to_dict()["score"][team.id]
        if not team_dict:
            return None

        team_dict["history"] = await get_history(team.reference)

        for m in team_dict["members"].values():
            user_id = m["id"]
            user_ref = firestore_async_db.collection("users").document(user_id)
            user = await user_ref.get()
            user_dict = user.to_dict()
            isSubscribed = user_dict.get(event_type, {}).get(event_id, {}).get("isSubscribed", False)
            m["isSubscribed"] = isSubscribed

    else:
        team_dict["members"] = await asyncio.gather(*[get_user(member, event_type=event_type, event_id=event_id) for member in team_dict.get("members", {}).values()])

    team_dict["id"] = team.id
    team_dict["is_owner"] = team_dict["owner"].id == user_id
    return team_dict


async def get_event(event_type: str, event_id: str):
    event = await firestore_async_db.collection_group(event_type).where("event_id", "==", event_id).limit(1).get()
    if len(event) == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return event[0]

# TODO: test this function, there might be some weird behavior with updating an existing team
# there might be some concurency going on when updating the user/team infos + scoring at the same time 
async def dispatch_on_team_update(event_type: str, event_ref, team_ref, team_dict, climbingLocation_id=None):
    """
    Do some manips depending on the event type when a team is updated
    + have a nested update in the event (don't erase the previous data)
    """

    def create_update_dict(path, object_dict, to_update):
        """nested update in firestore without erasing the previous data"""
        for key in object_dict:
            if isinstance(object_dict[key], dict) and object_dict[key]:
                to_update = create_update_dict(f"{path}.{key}", object_dict[key], to_update)
            else:
                to_update[f"{path}.{key}"] = object_dict[key]

        return to_update

    if event_type == "contest":
        # add the team to the "score" field in event
        to_update = create_update_dict(f"score.{team_ref.id}", team_dict, {})
        await event_ref.update(to_update)

    elif event_type == "vsl":
        # add the team to the "score" field in the league of the event
        if not climbingLocation_id:
            logging.error("No climbingLocation_id in team, not updating the league score")
            return

        league_ref = event_ref.collection("leagues").document(climbingLocation_id)
        to_update = create_update_dict(f"score.{team_ref.id}", team_dict, {})
        await league_ref.update(to_update)

    else:
        logging.warning(f"Event type {event_type} not found")

async def dispatch_on_team_delete(event_type: str, event_ref, team_id, climbingLocation_id=None):
    if event_type == "contest":
        await event_ref.update({f"score.{team_id}": firestore.DELETE_FIELD})

    elif event_type == "vsl":
        # remove the team from the "score" field in the league of the event
        if not climbingLocation_id:
            logging.error("No climbingLocation_id in team, not updating the league score")
            return
        
        league_ref = event_ref.collection("leagues").document(climbingLocation_id)
        await league_ref.update({f"score.{team_id}": firestore.DELETE_FIELD})

    else:
        logging.warning(f"Event type {event_type} not found")


async def impersonate_user(uid: str, to_impersonate_id: str):
    """Check if the user can impersonate the other user, return the user_id to use, else raise a 403"""

    if not to_impersonate_id:
        return uid

    my_user = await firestore_async_db.collection("users").document(uid).get()
    my_user_dict = my_user.to_dict()
    if not my_user_dict:
        raise HTTPException(status_code=404, detail="User not found")

    is_gym = my_user_dict.get("isGym", False)

    if not is_gym:
        raise HTTPException(status_code=403, detail="You are not allowed to impersonate a user")
    
    return to_impersonate_id


async def get_history(team_ref: firestore.AsyncDocumentReference, limit=10, offset=0):
    history = await (
        team_ref.collection("history")
        .order_by("date", direction=firestore.Query.DESCENDING)
        .limit(limit).offset(offset).get()
    )

    res = []
    for h in history:
        h_dict = h.to_dict()
        sentwall = await get_sentwall(h_dict.get("sentwall_ref"))
        if not sentwall:
            continue

        h_dict["sentWall"] = sentwall
        res.append(h_dict)

    return res