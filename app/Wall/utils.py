from concurrent.futures import ThreadPoolExecutor
from ..settings import firestore_db,firestore_async_db
import asyncio
import io

from PIL import Image, ImageOps

def get_sentwalls(user, secteur, wall_ref):
    sentWalls = (
        firestore_db.collection("users")
        .document(user.id)
        .collection("sentWalls")
        .where("wall", "==", secteur.collection("walls").document(wall_ref))
        .get()
    )
    for sentWall in sentWalls:
        sentWall_dict = sentWall.to_dict()
        sentWall_dict["id"] = sentWall.id
        if sentWall_dict["grade"]:
            grade_id = sentWall_dict["grade"].id
            sentWall_dict["grade"] = sentWall_dict["grade"].get().to_dict() if sentWall_dict["grade"] else None
            sentWall_dict["grade"]["id"] = grade_id

        sentWall_dict["date"] = sentWall_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
        sentWall_dict["wall"] = None
        sentWall_dict["user"] = {
            "id": user.id,
            "username": user.to_dict()["username"],
            "profile_image_url": (user.to_dict()["profile_image_url"] if "profile_image_url" in user.to_dict() else None),
        }
        return sentWall_dict


async def list_walls_sector(secteur, actual=True, uid=None):
    walls = secteur.reference.collection("walls").stream()
    walls_list = []
    walls_ref = []

    secteur_dict = secteur.to_dict()

    # if thumbnails are available, use them
    # reduces bandwidth usage
    thumbnails = secteur_dict.get("thumbnails", [])
    if thumbnails:
        secteur_dict["image"] = thumbnails

    secteur_dict = {
        "id": secteur.id,
        "label": secteur_dict.get("label", None),
        "newlabel": secteur_dict.get("newlabel", ""),
        "images": secteur_dict.get("image", []),
    } 

    async def get_wall(wall):
        wall_dict = wall.to_dict()
        wall_dict["id"] = wall.id
        wall_dict["isActual"] = actual
        wall_dict["secteur"] = secteur_dict
        wall_dict["isDone"] = uid in sentwalls_ref_to_uids(wall_dict.get("sentWalls", []))

        if "grade" in wall_dict and wall_dict["grade"]:
            grade = await wall_dict["grade"].get()
            grade_dict = grade.to_dict()

            if not grade_dict:
                return

            grade_dict["id"] = grade.id
            wall_dict["grade"] = grade_dict
        else:
            return

        walls_list.append(wall_dict)
        walls_ref.append(wall.reference)

    await asyncio.gather(*[get_wall(wall) async for wall in walls])
    return walls_list, walls_ref


async def get_wall(wall, secteur_dict, climbingLocation_dict, actual=True):
    wall_dict = wall.to_dict()
    wall_dict["id"] = wall.id
    wall_dict["isActual"] = actual
    wall_dict["isDone"] = False
    wall_dict["secteur"] = secteur_dict
    wall_dict["climbingLocation"] = climbingLocation_dict
    if ("grade" in wall_dict and wall_dict["grade"]):
        grade = await wall_dict["grade"].get()
        grade_dict = grade.to_dict()

        if not grade_dict:
            return

        grade_dict["id"] = grade.id
        wall_dict["grade"] = grade_dict
    elif "grade_id" in wall_dict:
        print("grade_id")
        return wall_dict
    else:
        return

    return wall_dict

async def image_to_thumbnail(contents, size=(320, 320)):
    tmp = Image.open(io.BytesIO(contents))
    tmp.thumbnail(size)
    tmp = ImageOps.exif_transpose(tmp)
    tmp = tmp.convert("RGB")

    imgByteArr = io.BytesIO()
    tmp.save(imgByteArr, format="JPEG")
    imgByteArr = imgByteArr.getvalue()

    return imgByteArr


async def get_project_data(projet):
    projet_dict = projet.to_dict()
    projet_dict["id"] = projet.id if projet.id else projet.reference.id

    #cloc id
    projet_dict["climbingLocation_id"] =  projet_dict["climbingLocation_ref"].id
    climbingLocation_ref = projet_dict["climbingLocation_ref"]
    climbingLocation_dict = await climbingLocation_ref.get()
    climbingLocation_dict = climbingLocation_dict.to_dict()
    climbingLocation_dict["id"] = climbingLocation_ref.id

    #get the wall data
    wall_ref = projet_dict["wall_ref"]
    wall = await wall_ref.get()
    # if the wall is not found, delete the project
    if not wall.exists:
        print("wall not found")
        await projet.reference.delete()
        return None


    #get secteur
    secteur_ref = projet_dict["secteur_ref"]
    secteur_dict = await secteur_ref.get()
    secteur_dict = secteur_dict.to_dict()
    secteur_dict["id"] = secteur_ref.id

    if "image" in secteur_dict:
        if isinstance(secteur_dict["image"], list):
            secteur_dict["images"] = secteur_dict["image"]
        elif isinstance(secteur_dict["image"], str):
            secteur_dict["images"] = [secteur_dict["image"]]
        else:
            secteur_dict["images"] = []

    projet_dict["wall_id"] = await get_wall(wall, secteur_dict, climbingLocation_dict)
    projet_dict["secteur_id"] = secteur_ref.id

    return projet_dict

async def get_grade(grade_ref):
    if not grade_ref:
        return None

    grade = await grade_ref.get()
    if not grade.exists:
        return None

    grade_dict = grade.to_dict()
    id = grade_ref.id
    grade_dict["id"] = id
    return grade_dict

async def calculate_points(vgrade, climbingLocation_id):
    if vgrade == None:
        return 0

    grades = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").stream()
    grades_list = [grade.to_dict() async for grade in grades]
    grades_list = sorted(grades_list, key=lambda x: x.get("vgrade", -1))
    grades_list = [grade for grade in grades_list if grade.get("ref1") != "?"] # exclude the grade "?"

    index = -1
    for i, g in enumerate(grades_list):
        if g.get("vgrade") == vgrade:
            index = i
            break

    if index == -1:
        return 0
    
    # get the points of the grade (round to the nearest 5)
    increments = 1000 / len(grades_list)
    points = increments * (index + 1)
    points = round(points / 5) * 5
    return points


def sentwalls_ref_to_uids(sentwalls):
    # users/uid/sentwalls/sentwall_id -> uid
    return [sentwall.parent.parent.id for sentwall in sentwalls]
