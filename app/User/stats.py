from ..settings import firestore_db, firestore_async_db, storage_client, BUCKET_NAME, app
from .utils import get_sentwall, filter_sentWall_with_climbingLocation
from .deps import get_current_user
from fastapi import Depends
from concurrent.futures import ThreadPoolExecutor
from google.cloud import firestore
from typing import List
from ..Wall.models import SentWallResp

from datetime import datetime, timedelta
import asyncio


@app.get("/api/v1/user/me/history-new/", response_model=List[SentWallResp])
async def get_user_history(
    limit: int = 10,
    offset: int = 0,
    climbingLocation_id: str = None,
    user_id: str = Depends(get_current_user)
    ):
    """Doesn't really make use of the limit / offset on the query side"""

    # sort by date + apply offset and limit
    sentWalls = await (
        firestore_async_db.collection("users")
        .document(user_id)
        .collection("sentWalls")
        .order_by("date", direction=firestore.Query.DESCENDING)
        .offset(offset)
        .limit(limit)
        .get()
    )

    if climbingLocation_id != None:
        sentWalls = filter_sentWall_with_climbingLocation(sentWalls, climbingLocation_id)

    sentWalls = sorted(sentWalls, key=lambda x: x.to_dict()["date"], reverse=True)
    ret = await asyncio.gather(*[get_sentwall(sentWall) for sentWall in sentWalls])
    return [r for r in ret if r] # remove None values

@app.get("/api/v1/user/me/history/")
async def get_user_history(user_id: str = Depends(get_current_user)):
    return await get_user_history(limit=10, user_id=user_id)


@app.get("/api/v1/user/me/stats/global/")
async def get_user_stats_global(
    filter_by: str = None,
    user_id: str = Depends(get_current_user),
):

    now = datetime.now()
    filter_start_date = None
    if filter_by == "week":
        filter_start_date = now - timedelta(days=7)
    elif filter_by == "month":
        filter_start_date = now - timedelta(days=30)
    elif filter_by == "year":
        filter_start_date = now - timedelta(days=365)

    if filter_start_date:
        sentWalls = firestore_async_db.collection("users").document(user_id).collection("sentWalls").where("date", ">=", filter_start_date).stream()
    else:
        sentWalls = firestore_async_db.collection("users").document(user_id).collection("sentWalls").stream()

    clocs = set()
    stats = {"sent_walls": 0, "climbingLocation": 0, "attributes": {}}

    async def process_sentWall(sentWall):
        sentWall_dict = sentWall.to_dict()
        if "wall" not in sentWall_dict:
            return
        wall_ref = sentWall_dict["wall"]
        wall = await wall_ref.get()
        wall_dict = wall.to_dict()
        if not wall.exists and not wall_dict:
            return
        
        activity_date = sentWall_dict.get("date")
        if filter_start_date is None or activity_date.timestamp() >= filter_start_date.timestamp():
            stats["sent_walls"] += 1
            climbingLocation_ref = wall_ref.parent.parent.parent.parent
            climbingLocation_id = climbingLocation_ref.id

            if climbingLocation_id not in clocs:
                stats["climbingLocation"] += 1
                clocs.add(climbingLocation_id)
            if "attributes" in wall_dict:
                for attribute in wall_dict["attributes"]:
                    if attribute in stats["attributes"]:
                        stats["attributes"][attribute] += 1
                    else:
                        stats["attributes"][attribute] = 1

    await asyncio.gather(*[process_sentWall(sentWall) async for sentWall in sentWalls])
    return stats


@app.get("/api/v1/user/me/stats/perGym/")
async def get_user_stats_perGym(filter_by: str = None, user_id: str = Depends(get_current_user)):
    perGym = {}
    now = datetime.now()

    filter_start_date = None
    if filter_by == "week":
        filter_start_date = now - timedelta(days=7)
    elif filter_by == "month":
        filter_start_date = now - timedelta(days=30)
    elif filter_by == "year":
        filter_start_date = now - timedelta(days=365)

    if filter_start_date:
        userActivities = firestore_async_db.collection("users").document(user_id).collection("sentWalls").where("date", ">=", filter_start_date).stream()
    else:
        userActivities = firestore_async_db.collection("users").document(user_id).collection("sentWalls").stream()

    async def get_stats_gym(sentWall):
        if "wall" not in sentWall.to_dict():
            return
        wall_ref = sentWall.to_dict()["wall"]
        
        wall = await wall_ref.get()
        wall_dict = wall.to_dict()
        sentWall_dict = sentWall.to_dict()

        if not wall.exists and not wall_dict:
            return

        date = sentWall_dict.get("date")
        if filter_start_date is None or date.timestamp() >= filter_start_date.timestamp():
            climbingLocation_ref = wall_ref.parent.parent.parent.parent
            climbingLocation_id = climbingLocation_ref.id

            # climbingLocation info
            if climbingLocation_id not in perGym:
                climbingLocation = await climbingLocation_ref.get()
                climbingLocation_dict = climbingLocation.to_dict()
                climbingLocation_dict["id"] = climbingLocation_id

                grades = [
                    {**grade.to_dict(), "id": grade.id}
                    async for grade in climbingLocation_ref.collection("grades").stream()
                ]
                grades.sort(key=lambda x: x["vgrade"])

                perGym[climbingLocation_id] = {
                    "climbingLocation": {
                        **climbingLocation_dict,
                        "grades": grades
                    }
                }

            # Number of sent wall per gym
            perGym[climbingLocation_id].setdefault("sent_walls", 0)
            perGym[climbingLocation_id]["sent_walls"] += 1

            # Number of sent wall per attributes
            perGym[climbingLocation_id].setdefault("attributes", {})
            if "attributes" in wall_dict:
                for attribute in wall_dict["attributes"]:
                    perGym[climbingLocation_id]["attributes"].setdefault(attribute, 0)
                    perGym[climbingLocation_id]["attributes"][attribute] += 1

            # Number of sent wall per color
            perGym[climbingLocation_id].setdefault("grade", {})

            if "grade" in wall_dict:
                grade = await wall_dict["grade"].get()
            elif "grade_id" in wall_dict:
                grade = await climbingLocation_ref.collection("grades").document(wall_dict["grade_id"]).get()
            else:
                # Pas de grade, pas de chocolat
                return

            grade_dict = grade.to_dict()
            if grade.exists and grade_dict:
                color = grade.to_dict()["ref1"]
                perGym[climbingLocation_id]["grade"].setdefault(color, 0)
                perGym[climbingLocation_id]["grade"][color] += 1

            # Number of sent wall per date
            perGym[climbingLocation_id].setdefault("date", {})
            date = date.strftime("%Y-%m-%d")
            perGym[climbingLocation_id]["date"].setdefault(date, [])
            perGym[climbingLocation_id]["date"][date].append(wall_dict)

            wall_dict["id"] = wall.id
            wall_dict["grade"] = grade_dict
            wall_dict["routesettername"] = None
            if grade.exists and grade_dict:
                wall_dict["grade"]["id"] = grade.id

            # some cleanup because of the spraywall format
            wall_dict.pop("sentWalls", None)
            wall_dict.pop("routesetter", None)

    await asyncio.gather(*[get_stats_gym(sentWall) async for sentWall in userActivities])
    return perGym
