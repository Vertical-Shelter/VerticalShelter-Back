import asyncio
import datetime

from google.cloud import firestore

from ..settings import firestore_async_db, ENV_MODE
from ..Wall.utils import get_grade

async def get_user(user_ref):
    user = await user_ref.get()
    user_id = user.id
    user_dict = user.to_dict()
    user_dict["id"] = user_id
    user_dict["climbingLocation_id"] = None

    return user_dict


async def fetch_vsl(vsl_id: str):
    vsl = await firestore_async_db.collection("vsl").document(vsl_id).get()
    if not vsl.exists:
        return None

    vsl_dict = vsl.to_dict()
    vsl_dict["id"] = vsl_id
    return vsl_dict


async def fetch_vsls():
    vsls = (
        firestore_async_db.collection("vsl")
        .stream()
    )
    res = []
    async for vsl in vsls:
        vsl_id = vsl.id
        vsl_dict = vsl.to_dict()
        vsl_dict["id"] = vsl_id
        res.append(vsl_dict)
    return res


async def fetch_join_requests(team_dict):
    async def get_req(user_id):
        team_dict["join_requests"][user_id]["user"] = await get_user(
            firestore_async_db.collection("users").document(user_id)
        )

    join_requests = team_dict.get("join_requests", {})
    await asyncio.gather(*[get_req(user_id) for user_id in join_requests.keys()])
    return team_dict


async def vsl_sentwall_scoring(wall: firestore.DocumentSnapshot, sentwall_ref: firestore.AsyncDocumentReference, user_id: str, sent=True):
    """Sent: True if the wall was sent, False if the wall was removed -> remove points"""
    cloc_id = wall.reference.parent.parent.parent.parent.id

    # get actual vsl
    vsls = (
        firestore_async_db.collection("vsl")
        .where("is_actual", "==", True)
        .order_by("end_date", direction=firestore.Query.ASCENDING)
        .limit(1)
        .stream()
    )

    # get the first vsl that has already started
    async for vsl in vsls:
        vsl_dict = vsl.to_dict()
        if vsl_dict.get("start_date") > datetime.datetime.now(datetime.timezone.utc):
            continue
        vsl_id = vsl.id
        break
    else:
        return
    
    # get user
    user = await firestore_async_db.collection("users").document(user_id).get()
    user_dict = user.to_dict()
    vsl_sub_dict = user_dict.get("vsl", {}).get(f"{vsl_id}", {})
    is_subscribed = vsl_sub_dict.get("isSubscribed", False)
    current_team_id = vsl_sub_dict.get("current_team", None)

    if ENV_MODE != "test" and (not is_subscribed or not current_team_id):
        # print(f"User {user_id} is not subscribed to the vsl {vsl_id}")
        return
    
    # get vsl team infos
    team = await firestore_async_db.collection("vsl").document(vsl_id).collection("teams").document(current_team_id).get()
    team_dict = team.to_dict()
    team_id = team.id

    if not team_dict or not (team_dict.get("climbingLocation_id") == cloc_id):
        # print(f"Team {current_team_id} not found or not in the same climbing location, vsl {vsl_id}")
        return

    user_role = None
    for role, uid in team_dict.get("roles", {}).items():
        if uid == user_id:
            user_role = role
            break

    # get the wall grade
    wall_dict = wall.to_dict()
    wall_id = wall.id

    grades = firestore_async_db.collection("climbingLocations").document(cloc_id).collection("grades").stream()
    grades_list = [grade.to_dict() async for grade in grades]
    grades_list = sorted(grades_list, key=lambda x: x.get("vgrade", -1))
    grades_list = [grade for grade in grades_list if grade.get("ref1") != "?"] # exclude the grade "?"

    def calculate_point(wall_grade):
        if not wall_grade:
            return 0
        
        index = -1
        for i, g in enumerate(grades_list):
            if g.get("vgrade") == wall_grade.get("vgrade"):
                index = i
                break

        if index == -1:
            return 0
        
        # get the points of the grade (round to the nearest 5)
        increments = 1000 / len(grades_list)
        points = increments * (index + 1)
        points = round(points / 5) * 5
        return points

    grade = await get_grade(wall_dict.get("grade"))
    raw_points = calculate_point(grade)

    vsl_attributes = wall_dict.get("vsl_attributes", []) # contains the role
    mult = 2 if user_role in vsl_attributes else 0.5
    points = int(raw_points * mult)

    if not sent:
        # if not in history, well don't remove points, must be an old sentwall or something
        histories = await team.reference.collection("history").where("sentwall_ref", "==", sentwall_ref).get()
        if len(histories) == 0:
            return

        # remove the sentwall from the team history
        for history in histories:
            await history.reference.delete()
        return

    # TODO: use old attributes if no vsl_attributes found

    # add sentwall to team history
    await firestore_async_db.collection("vsl").document(vsl_id).collection("teams").document(team_id).collection("history").add({
        "sentwall_ref": sentwall_ref,
        "points": points,
        "raw_points": raw_points,
        "user_id": user_id,
        "user_role": user_role,
        "date": datetime.datetime.now(datetime.timezone.utc),
        "vsl_attributes": vsl_attributes,
    })

    # add points to team
    await firestore_async_db.collection("vsl").document(vsl_id).collection("leagues").document(cloc_id).update({
        f"score.{team_id}.points": firestore.Increment(points),
        f"score.{team_id}.members.u_{user_id}.points": firestore.Increment(points),
    })

    return points

async def migrate_user_history(event_type, event_ref, climbingLocation_id, user_ref, from_team_ref, to_team_ref):
    if event_type != "vsl" or not from_team_ref or not to_team_ref:
        return
    
    league = await firestore_async_db.collection("vsl").document(event_ref.id).collection("leagues").document(climbingLocation_id).get()
    league_dict = league.to_dict()
    if not league_dict:
        return

    from_team = await from_team_ref.get()
    to_team = await to_team_ref.get()

    if not from_team.exists or not to_team.exists:
        return
    
    to_team_dict = to_team.to_dict()

    # get all the history of the team
    old_history = await from_team_ref.collection("history").where("user_id", "==", user_ref.id).get()
    old_history_dict = [h.to_dict() for h in old_history]

    if len(old_history_dict) == 0:
        return

    # recalculate the puntos of the user in the to_team + total points of both teams
    new_role = None
    for role, uid in to_team_dict.get("roles", {}).items():
        if uid == user_ref.id:
            new_role = role
            break

    if not new_role:
        print("Something wrong with the roles when migrating team point history")
        return

    # move history to the new team and calculate the new points
    batch = firestore_async_db.batch()
    new_points = 0
    for h in old_history_dict:
        raw_points = h.get("raw_points", 0)
        vsl_attributes = h.get("vsl_attributes", {})
        bloc_points = raw_points * (2 if new_role in vsl_attributes else 0.5)

        h["points"] = bloc_points
        h["user_role"] = new_role

        new_points += bloc_points
        batch.set(to_team_ref.collection("history").document(), h)


    batch.update(league, {
        f"score.{to_team.id}.points": firestore.Increment(new_points),
        f"score.{to_team.id}.members.u_{user_ref.id}.points": firestore.Increment(new_points),
    })

    # remove the old history from user
    for h in old_history:
        batch.delete(from_team_ref.collection("history").document(h.id))

    await batch.commit()


async def remove_user_points(event_type, event_ref, climbingLocation_id, user_ref, team_ref):
    # call this before removing the user from the team ( else there is no points to remove... :) )
    if event_type != "vsl":
        return

    league = await firestore_async_db.collection("vsl").document(event_ref.id).collection("leagues").document(climbingLocation_id).get()
    league_dict = league.to_dict()
    if not league_dict:
        return
    

    # a bit messy but it works
    user_points = league_dict.get("score", {}).get(team_ref.id, {}).get("members", {}).get(f"u_{user_ref.id}", {}).get("points", 0)
    if user_points == 0:
        return
    
    await league.reference.update({
        f"score.{team_ref.id}.points": firestore.Increment(-user_points),
    })
