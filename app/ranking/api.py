from fastapi import Depends, HTTPException
from concurrent.futures import ThreadPoolExecutor
from google.cloud import firestore
import asyncio

from ..settings import firestore_db, firestore_async_db, BUCKET_NAME, app
from ..User.deps import get_current_user
from .utils import get_ranking, get_ranking_friends, update_user_points_single
from ..Wall.models import *


@app.get("/api/v1/user/me/friends/ranking/")
async def get_ranking_from_friends(
    user_id: str = Depends(get_current_user)
):
    
    friends = await firestore_async_db.collection('users').document(user_id).collection('friends').get()
    friends_id = [friend.id for friend in friends]
    ranking_list = await get_ranking_friends("global", friends_id, user_id)

    return ranking_list


@app.get("/api/v1/user/ranking/global/")
async def get_ranking_global(
    offset : int = 0,
    limit : int = 0,
    user_id: str = Depends(get_current_user)
):
    ranking_list = await get_ranking("global")
    if limit == 0:
        return ranking_list

    filtered = ranking_list[offset:offset+limit]

    i = 0
    for user in ranking_list:
        if user["id"] == user_id:
            break
        i += 1

    if i < offset and i < len(ranking_list):
        filtered.insert(0, ranking_list[i])
    elif i > offset + limit and i < len(ranking_list):
        filtered.append(ranking_list[i])
    else:
        user = await firestore_async_db.collection("users").document(user_id).get()
        user_dict = user.to_dict()
        res = {
            "id": user.id,
            "username": user_dict["username"] if "username" in user_dict else None,
            "points": 0,
            "profile_image_url": user.to_dict().get("profile_image_url"),
            "rank": len(ranking_list) + 1
        }
        filtered.append(res)

    return filtered 

@app.get("/api/v1/user/ranking/{climbingLocation_id}/")
async def get_ranking_by_cloc(
    climbingLocation_id: str,
    offset: int = 0,
    limit: int = 0,
    user_id: str = Depends(get_current_user)
):
    if climbingLocation_id == "U4bSEMEpO6oiaNFVMxix":
        return []

    ranking_list = await get_ranking(climbingLocation_id)
    if limit == 0:
        return ranking_list

    filtered = ranking_list[offset:offset+limit]

    i = 0
    for user in ranking_list:
        if user["id"] == user_id:
            break
        i += 1

    if i < offset and i < len(ranking_list):
        filtered.insert(0, ranking_list[i])
    elif i > offset + limit and i < len(ranking_list):
        filtered.append(ranking_list[i])
    else:
        user = await firestore_async_db.collection("users").document(user_id).get()
        user_dict = user.to_dict()
        res = {
            "id": user.id,
            "username": user_dict["username"] if "username" in user_dict else None,
            "points": 0,
            "profile_image_url": user.to_dict().get("profile_image_url"),
            "rank": len(ranking_list) + 1
        }
        filtered.append(res)

    return filtered

@app.post("/api/v1/user/ranking/recalculate/")
async def recalculate_ranking(
    user_id: str = Depends(get_current_user),
):
    """Before calling it is best to remove all the ranking from the collection"""

    users = await firestore_async_db.collection("users").get()

    # ensure all clocs + global have a ranking
    async def ensure_exists(cloc_id):
        ranking_ref = firestore_async_db.collection("ranking").document(cloc_id)
        ranking = await ranking_ref.get()
        if not ranking.exists:
            await ranking_ref.set({})

    clocs = await firestore_async_db.collection("climbingLocations").get()
    clocs_id = [cloc.id for cloc in clocs] + ["global"]
    await asyncio.gather(*[ensure_exists(cloc_id) for cloc_id in clocs_id])

    async def process_user(user):
        sentWalls = await user.reference.collection("sentWalls").get()

        # group by climbingLocation_id
        sentWalls_dict = {}
        for sentwall in sentWalls:
            sentwall = sentwall.to_dict()

            if sentwall.get("wall").parent.parent.parent.id == "secteurs":
                cid = sentwall.get("wall").parent.parent.parent.parent.id
                if cid not in sentWalls_dict:
                    sentWalls_dict[cid] = []

                sentWalls_dict[cid].append(sentwall)

        async def get_walls_from_sentwall(sentwall):
            return await sentwall["wall"].get()

        async def update_points(cloc_id, sentWalls):
            if not cloc_id:
                print(f"User {user.id} has a sentWall without climbingLocation_id")
                return

            walls = await asyncio.gather(*[get_walls_from_sentwall(sentwall) for sentwall in sentWalls])
            cloc_ref = firestore_async_db.collection("climbingLocations").document(cloc_id)
            await update_user_points_single(cloc_ref, walls, user, True)

        # doesn't work cleanly because of firestore.increment weird behavior
        #await asyncio.gather(*[update_points(cloc_id, sentWalls) for cloc_id, sentWalls in sentWalls_dict.items()])

        for cloc_id, sentWalls in sentWalls_dict.items():
            await update_points(cloc_id, sentWalls)

    BATCH_SIZE = 50
    total_users = len(users)
    
    for i in range(0, total_users, BATCH_SIZE):
        batch = users[i:i + BATCH_SIZE]
        await asyncio.gather(*[process_user(user) for user in batch])
        print(f"Processed users {i + 1} to {min(i + BATCH_SIZE, total_users)} out of {total_users}")
