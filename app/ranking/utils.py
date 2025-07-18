from typing import List
from ..settings import firestore_db, firestore_async_db
import datetime
from firebase_admin import messaging
from google.cloud.firestore import AsyncTransaction, Increment

from fastapi_utils.tasks import repeat_every
from ..User.models import UserRankingResp
import asyncio


"""
Ranking avec des points fixes
Des que l'utilisateur sentwall, on update le point de l'utilisateur
Un mur vaut le nb de points qui correspondent au vgrade
meme principe quand on desent

Deux type de classment : global et par cloc
le classement global est la somme des clocs
il faut donc mettre à jour le classement global et le classement par cloc dans la meme fonction
"""

def strip_first_numbers(user_id):
    # remove the first numbers from the user_id to avoid firestore regex error
    res = ""
    for i in range(len(user_id)):
        c = user_id[i]
        if not c.isdigit():
            res = user_id[i:]
            break
    return res

async def update_ranking_by_id(ranking_id, user, points):
    #print(f"Updating ranking {ranking_id} for user {user.id} with {points} points")

    ranking_ref = firestore_async_db.collection("ranking").document(ranking_id)
    user_id_strip = strip_first_numbers(user.id)
    ranking = await ranking_ref.get([user_id_strip])

    ranking_dict = {}
    if not ranking.exists:
        await ranking_ref.set(ranking_dict)

    user_dict = user.to_dict()

    to_update = {
        f"{user_id_strip}.id": user.id,
        f"{user_id_strip}.points": Increment(points),
        f"{user_id_strip}.username": user_dict.get("username"),
        f"{user_id_strip}.profile_image_url": user_dict.get("profile_image_url"),
    }

    await ranking_ref.update(to_update)


async def update_ranking_by_ids(ranking_id, users: List, points: List):
    if len(users) == 0:
        return

    ranking_ref = firestore_async_db.collection("ranking").document(ranking_id)
    users_id_strip = [strip_first_numbers(user.id) for user in users]
    ranking = await ranking_ref.get(users_id_strip)

    if not ranking.exists:
        await ranking_ref.set({})

    to_update = {}
    for i in range(len(users)):
        user = users[i]
        user_strip = users_id_strip[i]
        user_dict = user.to_dict()

        to_update[f"{user_strip}.id"] = user.id
        to_update[f"{user_strip}.points"] = Increment(points[i])
        to_update[f"{user_strip}.username"] = user_dict.get("username")
        to_update[f"{user_strip}.profile_image_url"] = user_dict.get("profile_image_url")

    await ranking_ref.update(to_update)


async def update_user_points_single(cloc_ref, walls: List, user, is_sent: bool):
    """Multiple walls at the same time in a single request"""

    async def get_grade(wall):
        if not wall or not wall.exists:
            return None

        wall_dict = wall.to_dict()
        grade_ref = wall_dict.get("grade")
        if not grade_ref:
            return None
        
        grade = await grade_ref.get()
        grade_dict = grade.to_dict()

        if not grade_dict:
            return None
        elif grade_dict.get("ref") == "?":
            return None

        return grade_dict

    wall_grades = await asyncio.gather(*[get_grade(wall) for wall in walls])

    # get all grades
    grades = await cloc_ref.collection("grades").get()
    grades_list = [grade.to_dict() for grade in grades]
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
    
    points = sum([calculate_point(wall_grade) for wall_grade in wall_grades])
    if not is_sent:
        points = -points

    if points == 0:
        return

    # return await asyncio.gather(*[update_ranking_by_id(ranking_id, user, points) for ranking_id in (cloc_ref.id, "global")])
    return await update_ranking_by_id(cloc_ref.id, user, points) #TOFIX only updates the cloc ranking

async def update_user_points_multiple(cloc_ref, all_walls: List, walls_list: List[List], users: List, is_sent: bool):
    """Multiple walls at the same time in a single request for multiple users"""

    walls_grades_mapping = {}
    async def get_grade(wall):
        if not wall.exists:
            return None

        wall_dict = wall.to_dict()
        grade_ref = wall_dict.get("grade")
        if not grade_ref:
            return None
        
        grade = await grade_ref.get()
        grade_dict = grade.to_dict()

        if not grade_dict:
            return None
        elif grade_dict.get("ref") == "?":
            return None
        
        walls_grades_mapping[wall.id] = grade_dict
        return grade_dict

    # get all wall grades 
    await asyncio.gather(*[get_grade(wall) for wall in all_walls])

    # get all cloc grades
    grades = await cloc_ref.collection("grades").get()
    grades_list = [grade.to_dict() for grade in grades]
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
    
    points_list = []
    for walls in walls_list:
        wall_grades = [walls_grades_mapping.get(wall.id) for wall in walls]
        points = sum([calculate_point(wall_grade) for wall_grade in wall_grades])
        if not is_sent:
            points = -points

        points_list.append(points)

    if all([p == 0 for p in points_list]):
        return

    # return await asyncio.gather(*[update_ranking_by_ids(ranking_id, users, points_list) for ranking_id in (cloc_ref.id, "global")])
    return await update_ranking_by_ids(cloc_ref.id, users, points_list) #TOFIX only updates the cloc ranking

# TODO: cache this
async def get_ranking(rank_id):
    ranking = await firestore_async_db.collection("ranking").document(rank_id).get()
    ranking_dict = ranking.to_dict()

    # remove the ranking key (deprecated)
    if "ranking" in ranking_dict:
        ranking_dict.pop("ranking")

    ranking_list = list(ranking_dict.values())
    ranking_list.sort(key=lambda x: x['points'], reverse=True)
    for i, user in enumerate(ranking_list):
        user["rank"] = i + 1

    return ranking_list

async def get_ranking_friends(rank_id, friends_id, user_id):
    to_fetch = [user_id] + friends_id
    to_fetch_strip = [strip_first_numbers(user_id) for user_id in to_fetch]
    ranking = await firestore_async_db.collection("ranking").document(rank_id).get(to_fetch_strip)
    ranking_dict = ranking.to_dict()

    # add the missing users
    for user_id in to_fetch:
        if strip_first_numbers(user_id) not in ranking_dict:
            user = await firestore_async_db.collection("users").document(user_id).get()
            user_dict = user.to_dict()

            ranking_dict[user_id] = {
                "id": user_id,
                "username": user_dict.get("username"),
                "points": 0,
                "profile_image_url": user_dict.get("profile_image_url"),
                "baniere": None,
            }

    ranking_list = list(ranking_dict.values())
    ranking_list.sort(key=lambda x: x['points'], reverse=True)
    for i, user in enumerate(ranking_list):
        user["rank"] = i + 1

    return ranking_list