import asyncio
import datetime
from typing import List, Optional

from fastapi import (BackgroundTasks, Body, Depends, File, Form, HTTPException,
                     UploadFile, concurrency)
from google.cloud import firestore

from ..news.utils import handle_notif
from ..ranking.utils import (update_user_points_multiple,
                             update_user_points_single)
from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        storage_client, ENV_MODE)
from ..Stats.utils import upload_sentwall_stats
from ..User.deps import get_current_user
from ..User.skills import Skill, updateSkillLess, updateSkillPlus
from ..User.utils import get_user_mini
from ..utils import send_file_to_storage
from ..VSL.utils import vsl_sentwall_scoring
from .models import CommentResp, LikeResp, SentWallResp, WallParam, WallResp
from .utils import (calculate_points, get_grade, image_to_thumbnail,
                    list_walls_sector, sentwalls_ref_to_uids)

# attributes

elements_sans_prehensions = [
    "Souplesse",
    "A doigts",
    "Physique",
    "Fissure",
    "Coordinations",
    "Dynamisme",
    "No foot",
    "Départ assis",
    "Résistance",
    "Traversée",
    "Placement",
    "Tenue de prises",
    "Technique",
    "Spatule",
    "Talon",
    "Lolotte",
    "Genou",
    "Bloc",
    "Volume",
    "Dièdre",
    "Tenue de prise",
    "A méthode",
    "Run and jump",
    "Gainage",
    "Pose de pied",
    "Basique",
    "Equilibre",
    "Compression",
    "Jeté",
    "Petit gabarit",
    "Croisé",
    "Réta",
    "Triceps",
    "Opposition",
    "Yaniro",
    "Horloge",
    "Adhérence",
]

# Liste des préhensions
prehensions = ["Reglette", "Arquée", "Pince", "Plat", "Bi doigt", "Mono doigt", "Bac", "Micro", "Macro", "Poignée", "Paumeau"]
liste_attributes = sorted(elements_sans_prehensions) + sorted(prehensions)

@app.get("/api/v1/wall/getattributes/")
async def get_attributes(user_id: str = Depends(get_current_user)):
    return {"attributes": liste_attributes}

# TODO: refacto
@app.get("/api/v1/climbingLocation/{climbingLocation_id}/list-all-walls/")
def get_list_walls(climbingLocation_id: str, user_id: str = Depends(get_current_user)):
    raise HTTPException(200, {"error": "Not implemented"})


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/list-actual-walls/", response_model=List[WallResp], response_model_exclude_unset=True)
async def get_list_walls(
    climbingLocation_id: str,
    uid: str = Depends(get_current_user)
):
    # Get all secteurs
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    secteurs = doc_ref.collection("secteurs").stream()
    res = await asyncio.gather(*[list_walls_sector(secteur, uid=uid) async for secteur in secteurs])

    walls_list = []
    refs = []

    for walls, walls_ref in res:
        walls_list.extend(walls)
        refs.extend(walls_ref)

    async def beta_ouvreur(wall, ref):
        if wall["betaOuvreur"]:
            return
        
        betas = firestore_async_db.collection_group("sentWalls").where("wall", "==", ref).where("beta", ">=", "").limit(1).stream()
        async for beta in betas:
            wall["betaOuvreur"] = beta.to_dict()["beta"]
            break

    beta_ouvreur_tasks = [beta_ouvreur(wall, ref) for wall, ref in zip(walls_list, refs)]
    await asyncio.gather(*beta_ouvreur_tasks)
    return walls_list


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/list-old-walls/", response_model=List[WallResp], response_model_exclude_unset=True)
async def get_list_old_walls(
    climbingLocation_id: str,
    limit: int = 10,
    start_after_secteur_id: str = None,
    uid: str = Depends(get_current_user)
):
    #Get old secteurs
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    query = doc_ref.collection("old_secteur").order_by("newlabel")

    if start_after_secteur_id:
        snapshot = await doc_ref.collection("old_secteur").document(start_after_secteur_id).get()
        query = query.start_after(snapshot)
    secteurs = query.limit(limit).stream()

    res = await asyncio.gather(*[list_walls_sector(secteur, actual=False) async for secteur in secteurs])

    walls_list = []
    refs = []

    for walls, walls_ref in res:
        walls_list.extend(walls)
        refs.extend(walls_ref)
    return walls_list


# secteur
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/")
def create_secteur(
    climbingLocation_id: str,
    user_id: str = Depends(get_current_user),
    label: str = Form(None),
    newlabel: str = Form(None),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteurs = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").stream()
    for secteur in secteurs:
        if label and secteur.to_dict()["label"] == label:
            return {"id": secteur.id, "label": label}
        if newlabel and "newlabel" in secteur.to_dict() and secteur.to_dict()["newlabel"] == newlabel:
            return {"id": secteur.id, "newlabel": newlabel}
    if newlabel:
        ref = (
            firestore_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("secteurs")
            .add(
                {
                    "newlabel": newlabel,
                }
            )
        )
        return {"id": ref[1].id, "newlabel": newlabel}

    if label:
        ref = (
            firestore_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("secteurs")
            .add(
                {
                    "label": label,
                }
            )
        )
        return {"id": ref[1].id, "label": label}


@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/")
async def put_secteur(
    climbingLocation_id: str,
    secteur_ref: str,
    user_id: str = Depends(get_current_user),
    image: list[UploadFile] = File(...),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).get().to_dict()
    if secteur == None:
        raise HTTPException(400, {"error": "Secteur not found"})
    
    current_images = secteur.get("image", [])
    current_images_fn = [url.split("/")[-1] for url in current_images]
    base_url = "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/"

    if image:
        image_list = []
        thumbnails = []
        for _image in image:

            # don't upload previously uploaded images
            if _image.filename in current_images_fn:
                image_list.append(f"{base_url}secteurs/{climbingLocation_id}/{secteur_ref}/{_image.filename}")
                thumbnails.append(f"{base_url}secteurs/{climbingLocation_id}/{secteur_ref}/thumb_{_image.filename}")
                continue

            contents = await _image.read()
            thumb_img = await image_to_thumbnail(contents)

            blob = storage_client.bucket(BUCKET_NAME).blob(f"secteurs/{climbingLocation_id}/{secteur_ref}/{_image.filename}")
            blob.upload_from_string(contents, content_type=_image.content_type)
            image_list.append(blob.public_url)

            blob = storage_client.bucket(BUCKET_NAME).blob(f"secteurs/{climbingLocation_id}/{secteur_ref}/thumb_{_image.filename}")
            blob.upload_from_string(thumb_img, content_type=_image.content_type)
            thumbnails.append(blob.public_url)

        # update secteur image
        firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).update(
            {
                "image": image_list,
                "thumbnails": thumbnails,
            }
        )

    return {"message": "Secteur updated successfully"}


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/migrate_to_old_secteur/")
async def migrate_to_old_secteur(
    climbingLocation_id: str,
    secteur_ref: str,
    user_id: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    climbingLocation = await doc_ref.get()
    climbingLocation_dict = climbingLocation.to_dict()
    if not climbingLocation.exists:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteur = await doc_ref.collection("secteurs").document(secteur_ref).get()
    if not secteur.exists:
        raise HTTPException(200, {"Warning": "Secteur not found"})
    secteur_dict = secteur.to_dict()

    # walls to migrate
    walls_from_db = await (
        firestore_async_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("secteurs")
        .document(secteur_ref)
        .collection("walls")
        .get()
    )

    # create old secteur with current walls and secteur data
    _, new_sector_ref = await (
        firestore_async_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("old_secteur")
        .add(
            {
                "label": secteur_dict.get("label"),
                "newlabel": secteur_dict.get("newlabel"),
                "image": secteur_dict.get("image", []),
            }
        )
    )

    to_update = {}
    async def migrate_wall(wall):
        # migrate walls to old_secteur collection and delete them from secteur collection
        wall_dict = wall.to_dict()
        wall_dict["id"] = wall.id
        _, new_wall_ref = await new_sector_ref.collection("walls").add(wall_dict)

        batch = firestore_async_db.batch()

        # update users sentWalls
        sentWalls = firestore_async_db.collection_group("sentWalls").where("wall", "==", wall.reference).stream()
        async for sentWall in sentWalls:
            user_to_update = sentWall.reference.parent.parent
            to_update.setdefault(user_to_update.id, []).append(new_wall_ref)

            batch.update(sentWall.reference, {
                "wall": new_wall_ref
            })

        # update likes and comments
        likes = wall.reference.collection("likes").stream()
        async for like in likes:
            batch.set(new_wall_ref.collection("likes").document(like.id), like.to_dict())
            batch.delete(like.reference)

        comments = wall.reference.collection("comments").stream()
        async for comment in comments:
            batch.set(new_wall_ref.collection("comments").document(comment.id), comment.to_dict())
            batch.delete(comment.reference)

        batch.delete(wall.reference)
        await batch.commit()

        return await new_wall_ref.get()

    all_walls = await asyncio.gather(*[migrate_wall(wall) for wall in walls_from_db])

    # prepare to update user points
    users_ids = list(to_update.keys())
    walls_list = list(to_update.values())

    users = await asyncio.gather(*[firestore_async_db.collection("users").document(user_id).get() for user_id in users_ids])
    await update_user_points_multiple(doc_ref, all_walls, walls_list, users, is_sent=False)

    # create user news
    # await create_user_news(UserNews(newsType="Gym", gym_id=climbingLocation_id, gym_type="NEW_SECT"), user_id)

    await handle_notif(
        "NEW_SECT",
        [f"{climbingLocation_dict["name"]} {climbingLocation_dict["city"]} - "],
        [f"{climbingLocation_dict["name"]} {climbingLocation_dict["city"]}"],
        notif_topic=climbingLocation_id,
        climbingLocation_id=climbingLocation_id,
    )

    return {"message": "Secteur updated successfully"}


# Wall
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/", response_model=WallResp)
async def create_wall(
    climbingLocation_id: str,
    secteur_id: str,
    wall_data: WallParam = Form(...),
    betaOuvreur: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)

    # get cloc
    climbingLocation = await doc_ref.get()
    climbingLocation_dict = climbingLocation.to_dict()
    if not climbingLocation_dict:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get grade
    secteur = await doc_ref.collection("secteurs").document(secteur_id).get()
    secteur_dict = secteur.to_dict()
    if not secteur_dict:
        raise HTTPException(400, {"error": "Secteur not found"})

    # get grade
    grade = await doc_ref.collection("grades").document(wall_data.grade_id).get()
    if not grade.exists:
        raise HTTPException(400, {"error": "Grade not found"})

    # upload betaOuvreur
    if betaOuvreur and not beta_url:
        beta_url = await send_file_to_storage(
            betaOuvreur, f"walls/{climbingLocation_id}/{secteur_id}/{betaOuvreur.filename}", betaOuvreur.content_type
        )

    if wall_data.date:
        creation_date = wall_data.date
    else:
        creation_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "attributes": wall_data.attributes,
        "grade": grade.reference,
        "description": wall_data.description,
        "hold_to_take": wall_data.hold_to_take,
        "betaOuvreur": beta_url,
        "routesettername": wall_data.routesettername,
        "vsl_attributes": wall_data.vsl_attributes,
        "date": creation_date,
    }

    _, new_wall = await secteur.reference.collection("walls").add(data)

    listNewLabel = climbingLocation_dict["listNewLabel"] if "listNewLabel" in climbingLocation_dict else []
    listUpdated = climbingLocation_dict["listUpdated"] if "listUpdated" in climbingLocation_dict else []

    # remove all newlabel if position in updated is more than 1 day
    length = len(listNewLabel)
    i = 0
    while i < length:
        if (datetime.datetime.now(datetime.timezone.utc) - listUpdated[i]).days > 1:
            listNewLabel.pop(i)
            listUpdated.pop(i)
            length -= 1
        elif listNewLabel[i] == secteur_dict["newlabel"]:
            listNewLabel.pop(i)
            listUpdated.pop(i)
            length -= 1
        else:
            i += 1

    secteur_label = secteur_dict["newlabel"] if "newlabel" in secteur_dict else secteur_dict["label"] if "label" in secteur_dict else None

    listNewLabel.append(secteur_label)
    listUpdated.append(datetime.datetime.now())

    # listNext Secteur to update
    listNextSecteur = climbingLocation_dict["listNextSector"] if "listNextSector" in climbingLocation_dict else []
    if secteur_label in listNextSecteur:
        listNextSecteur.remove(secteur_label)

    await doc_ref.update(
        {
            "newSector": secteur_label,
            "listNewLabel": listNewLabel,
            "listUpdated": listUpdated,
            "listNextSector": listNextSecteur,
        }
    )

    return {
        "id": new_wall.id,
        **data,
        "isActual": True,
        "secteur": {"id": secteur_id, "label": secteur_label, "newlabel": secteur_label, "images": secteur_dict["image"]},
        "grade": {"id": grade.id, **grade.to_dict()},
    }


@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/", response_model=WallResp)
async def put_wall(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
    wall_data: WallParam = Form(...),
    betaOuvreur: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).get().to_dict()
    if secteur == None:
        raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall_db = (
        firestore_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("secteurs")
        .document(secteur_ref)
        .collection("walls")
        .document(wall_ref)
        .get()
        .to_dict()
    )
    if wall_db == None:
        raise HTTPException(400, {"error": "Wall not found"})

    # update wall data
    data = {
        "attributes": wall_data.attributes,
        "grade": firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(wall_data.grade_id),
        "description": wall_data.description,
        "hold_to_take": wall_data.hold_to_take,
        "routesettername": wall_data.routesettername,
        "vsl_attributes": wall_data.vsl_attributes,
    }

    if betaOuvreur and not beta_url:
        beta_url = await send_file_to_storage(
            betaOuvreur, f"walls/{climbingLocation_id}/{secteur_ref}/{betaOuvreur.filename}", betaOuvreur.content_type
        )
    
    if beta_url:
        data["betaOuvreur"] = beta_url

    if wall_data.date:
        data["date"] = wall_data.date

    (
        firestore_db
        .collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("secteurs")
        .document(secteur_ref)
        .collection("walls")
        .document(wall_ref)
        .update(data)
    )

    grade_dict = data["grade"].get().to_dict()
    grade_dict["id"] = data["grade"].id
    wall_dict = {
        "id": wall_ref,
        "attributes": wall_data.attributes,
        "grade": grade_dict,
        "description": wall_data.description,
        "hold_to_take": wall_data.hold_to_take,
        "routesettername": wall_data.routesettername,
        "date": data.get("date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "secteur": {
            "id": secteur_ref,
            "label": secteur["label"] if "label" in secteur else None,
            "newlabel": secteur["newlabel"] if "newlabel" in secteur else None,
            "images": secteur["image"],
        },
    }
    return wall_dict


@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/")
async def patch_all_walls(
    climbingLocation_id: str,
    secteur_ref: str,
    image: list[UploadFile] = File(...),
    walls_data: list[WallParam] = Body(...),
    user_id: str = Depends(get_current_user),
    betaOuvreur: list[Optional[UploadFile]] = File(None),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).get().to_dict()
    if secteur == None:
        raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    walls_from_db = (
        firestore_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("secteurs")
        .document(secteur_ref)
        .collection("walls")
        .get()
    )

    for index, wall in enumerate(walls_data):
        if wall.wall_id:
            wall_ref = wall.wall_id
            wall_db = (
                firestore_db.collection("climbingLocations")
                .document(climbingLocation_id)
                .collection("secteurs")
                .document(secteur_ref)
                .collection("walls")
                .document(wall_ref)
                .get()
                .to_dict()
            )
            if wall_db == None:
                raise HTTPException(400, {"error": "Wall not found"})
            # # if betaOuvreur:
            # betaOuvreurUrl = await send_file_to_storage(betaOuvreur[index], f"walls/{climbingLocation_id}/{secteur_ref}/{betaOuvreur[index].filename}", betaOuvreur[index].content_type)

            data = {
                "attributes": wall.attributes,
                "grade": firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(wall.grade_id),
                "description": wall.description,
                "betaOuvreur": None,
                "hold_to_take": wall.hold_to_take,
                "routesettername": wall.routesettername,
            }
            firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).collection(
                "walls"
            ).document(wall_ref).update(data)
        else:
            data = {
                "attributes": wall.attributes,
                "grade": firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(wall.grade_id),
                "description": wall.description,
                "hold_to_take": wall.hold_to_take,
                # 'betaOuvreur': betaOuvreurUrl if betaOuvreurUrl else None,
                "routesettername": wall.routesettername,
            }
            firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).collection(
                "walls"
            ).add(data)

    if image:
        image_list = []
        for _image in image:
            image_list.append(await send_file_to_storage(_image, f"walls/{climbingLocation_id}/{secteur_ref}/{_image.filename}", _image.content_type))
        # update secteur image
        firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).update(
            {
                "image": image_list,
            }
        )

    return {"message": "secteur update successfully"}


@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/")
def delete_wall(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).get().to_dict()
    if secteur == None:
        raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall = (
        firestore_db.collection("climbingLocations")
        .document(climbingLocation_id)
        .collection("secteurs")
        .document(secteur_ref)
        .collection("walls")
        .document(wall_ref)
    )
    if wall.get().to_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})
    wall.delete()
    return {"message": "Wall deleted successfully"}


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/{wall_id}/", response_model=WallResp, response_model_exclude_unset=True)
async def get_wall(
    climbingLocation_id: str,
    secteur_id: str,
    wall_id: str,
    user_id: str = Depends(get_current_user),
):
    # can probably remove this
    async def check_cloc():
        cloc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
        climbingLocation = await cloc_ref.get()
        if not climbingLocation.exists:
            raise HTTPException(400, {"error": "ClimbingLocation not found"})
        return climbingLocation

    async def check_secteur():
        # check if secteur is old or new
        secteur = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_id).get()
        if not secteur.exists:
            secteur = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_id).get()
            if not secteur.exists:
                raise HTTPException(400, {"error": "Secteur not found"})
        return secteur

    climbingLocation, secteur = await asyncio.gather(check_cloc(), check_secteur())
    secteur_dict = secteur.to_dict()

    wall_ref = secteur.reference.collection("walls").document(wall_id)
    wall = await wall_ref.get()
    if not wall.exists:
        raise HTTPException(400, {"error": "Wall not found"})

    wall_dict = wall.to_dict()

    # get list of all sent to this wall
    sentWalls_stream = firestore_async_db.get_all(wall_dict.get("sentWalls", []))
    comments_stream = wall_ref.collection("comments").stream()

    async def get_sentWall(sentWall):
        if not sentWall.exists:
            return None

        sentWall_dict = sentWall.to_dict()
        sentWall_dict["id"] = sentWall.id
        sentWall_dict["wall"] = None

        user_ref = sentWall.reference.parent.parent
        if user_ref.id == user_id:
            wall_dict["isDone"] = True

        grade_ref = sentWall_dict["grade"]
        user_task = get_user_mini(user_ref)
        grade_task = get_grade(grade_ref)

        user_dict, grade_dict = await asyncio.gather(user_task, grade_task)
        sentWall_dict["user"] = user_dict
        sentWall_dict["grade"] = grade_dict
        return sentWall_dict
    
    async def get_comments(comment_ref):
        comment_dict = comment_ref.to_dict()
        comment_dict["id"] = comment_ref.id
        comment_dict["user"] = await get_user_mini(comment_dict.get("user"))
        return comment_dict

    list_sent_walls, comments = await asyncio.gather(
        asyncio.gather(*[get_sentWall(sentWall) async for sentWall in sentWalls_stream]),
        asyncio.gather(*[get_comments(comment_ref) async for comment_ref in comments_stream]),
    )

    list_sent_walls = [sentWall for sentWall in list_sent_walls if sentWall is not None]

    wall_dict["id"] = wall_id
    wall_dict["routesettername"] = None
    wall_dict["secteur"] = secteur_dict
    wall_dict["secteur"]["id"] = secteur_id

    grade_dict = await get_grade(wall_dict["grade"])
    wall_dict["grade"] = grade_dict
    wall_dict["points"] = await calculate_points(grade_dict.get("vgrade"), climbingLocation_id)
    wall_dict["sentWalls"] = list_sent_walls
    wall_dict["comments"] = comments

    return wall_dict


# climbers
@app.get("/api/v1/climbingLocation/{climbingLocation_id}/secteur/", response_model=List[WallResp], response_model_exclude_unset=True)
async def list_walls(climbingLocation_id: str, uid: str = Depends(get_current_user)):
    # Get all secteurs
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    secteurs = doc_ref.collection("secteurs").stream()
    res_sectors = await asyncio.gather(*[list_walls_sector(secteur, uid=uid) async for secteur in secteurs])

    walls_list_actual = []
    refs = []

    for walls, r in res_sectors:
        walls_list_actual.extend(walls)
        refs.extend(r)

    async def beta_ouvreur(wall, ref):
        if wall["betaOuvreur"]:
            return
        
        betas = firestore_async_db.collection_group("sentWalls").where("wall", "==", ref).where("beta", ">=", "").limit(1).stream()
        async for beta in betas:
            wall["betaOuvreur"] = beta.to_dict()["beta"]
            break

    beta_ouvreur_tasks = [beta_ouvreur(wall, ref) for wall, ref in zip(walls_list_actual, refs)]
    await asyncio.gather(*beta_ouvreur_tasks)

    # sort walls by newSector and vgrade and put newSector first
    walls_list_actual = sorted(walls_list_actual, key=lambda k: k["grade"]["vgrade"])
    return walls_list_actual


# comment
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/{wall_id}/comments/", response_model=CommentResp)
async def create_comment(
    climbingLocation_id: str,
    secteur_id: str,
    wall_id: str,
    user_id: str = Depends(get_current_user),
    comment: str = Form(...),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    secteur_ref = doc_ref.collection("secteurs").document(secteur_id)
    bloc_ref = secteur_ref.collection("walls").document(wall_id)
    comments_collection = bloc_ref.collection("comments")
    user_ref = firestore_async_db.collection("users").document(user_id)
    comment_dict = {
        "user": user_ref,
        "comment": comment,
        "date": datetime.datetime.now(),
    }

    _, ref = await comments_collection.add(comment_dict)
    comment_id = ref.id

    comment_dict.update({"id": comment_id})
    comment_dict["date"] = comment_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    
    user_dict = (await user_ref.get()).to_dict()
    comment_dict["user"] = user_dict
    comment_dict["user"]["id"] = user_id

    gyms = (
        firestore_async_db.collection("users")
        .where("isGym", "==", True)
        .where("climbingLocation_id", "==", doc_ref)
        .stream()
    )
    
    # send notification to gym
    async for gym in gyms:
        await handle_notif(
            "COMMENT",
            [user_dict['username']],
            [comment],
            dest_user=gym,
            climbingLocation_id=climbingLocation_id,
            secteur_id=secteur_id,
            wall_id=wall_id,
        )
        
    return comment_dict


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/comments/", response_model=List[CommentResp])
def get_comments(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    wall_dict = wall.get().to_dict()
    if wall_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    comments = wall.collection("comments").stream()
    comments_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        comment_dict["id"] = comment.id
        comment_dict["user"] = {
            "id": comment_dict["user"].id,
            "username": comment_dict["user"].get().to_dict()["username"],
            "profile_image_url": (
                comment_dict["user"].get().to_dict()["profile_image_url"] if "profile_image_url" in comment_dict["user"].get().to_dict() else None
            ),
        }
        comment_dict["date"] = comment_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
        comments_list.append(comment_dict)
    return comments_list

# delete comment
@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/comments/")
def delete_comment(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    comment_id: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    wall_dict = wall.get().to_dict()
    if wall_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    comment = wall.collection("comments").document(comment_id)
    comment.delete()
    return {"message": "Comment deleted successfully"}


# edit comment
@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/comments/")
def edit_comment(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    comment_id: str,
    message: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    wall_dict = wall.get().to_dict()
    if wall_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    comment = wall.collection("comments").document(comment_id)
    comment.update(
        {
            "message": message,
        }
    )
    return {"message": "Comment updated successfully"}


# likes
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/likes/", response_model=LikeResp)
def create_like(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})
    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    if wall.get().to_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    # check if user already like this wall
    data = {
        "user": firestore_db.collection("users").document(user_id),
        "date": datetime.datetime.now(),
    }
    wall.collection("likes").add(
        data
    )

    data["user"] = data["user"].get().to_dict()
    data["user"]["id"] = user_id
    data['date']    = data['date'].strftime("%Y-%m-%d %H:%M:%S")
    data["id"] = "like_id"
    updateSkillPlus(Skill.Analytique_Averti, firestore_db.collection("users").document(user_id), 10)

    return data


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/likes/", response_model=List[LikeResp])
def get_likes(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})
    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    if wall.get().to_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    # find all users who like this wall

    likes = wall.collection("likes").stream()
    likes_list = []
    for like in likes:
        like_dict = like.to_dict()
        like_dict["id"] = like.id
        user_id = like_dict["user"].id

        like_dict["user"] = like_dict["user"].get().to_dict()
        like_dict["user"]["id"] = user_id
        like_dict["user"]["climbingLocation_id"] = None
        like_dict["date"] = like_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
        # like_dict["avatar"] = None
        # like_dict[""]
        likes_list.append(like_dict)
    return likes_list


@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/likes/")
def delete_like(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    user_id: str = Depends(get_current_user),
):
    climbingLocation = firestore_db.collection("climbingLocations").document(climbingLocation_id).get().to_dict()
    if climbingLocation == None:
        raise HTTPException(400, {"error": "ClimbingLocation not found"})

    # get secteur and old-secteur to updates
    secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref)
    secteur_dict = secteur.get().to_dict()
    if secteur_dict == None:
        secteur = firestore_db.collection("climbingLocations").document(climbingLocation_id).collection("old_secteur").document(secteur_ref)
        secteur_dict = secteur.get().to_dict()
        if secteur_dict == None:
            raise HTTPException(400, {"error": "Secteur not found"})

    # update walls
    wall = secteur.collection("walls").document(wall_ref)
    if wall.get().to_dict == None:
        raise HTTPException(400, {"error": "Wall not found"})

    # check if user already like this wall
    likes = wall.collection("likes").where("user", "==", firestore_db.collection("users").document(user_id)).get()
    if len(likes) == 0:
        raise HTTPException(400, {"error": "User doesn't like this wall"})

    for like in likes:
        like.reference.delete()
    updateSkillLess(Skill.Analytique_Averti, firestore_db.collection("users").document(user_id), 10)

    return {"message": "like deleted successfully"}


# SentWall
@app.post("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/{wall_id}/sentwall/", response_model=SentWallResp)
async def create_sentwall(
    climbingLocation_id: str,
    secteur_id: str,
    wall_id: str,
    background_tasks: BackgroundTasks,
    date: Optional[datetime.datetime] = Form(None),
    beta: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    nTentative: Optional[int] = Form(None),
    user_id: str = Depends(get_current_user),
):
    cloc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    secteur_ref = cloc_ref.collection("secteurs").document(secteur_id)

    async def check_cloc():
        climbingLocation = await cloc_ref.get()
        if not climbingLocation.exists:
            raise HTTPException(400, {"error": "ClimbingLocation not found"})
        return climbingLocation
    
    async def check_secteur():
        secteur = await secteur_ref.get()
        if not secteur.exists:
            raise HTTPException(400, {"error": "Secteur not found"})
        return secteur
    
    async def check_user():
        user = await firestore_async_db.collection("users").document(user_id).get()
        if not user.exists:
            raise HTTPException(400, {"error": "User not found"})
        return user
    
    async def check_wall():
        wall = await secteur_ref.collection("walls").document(wall_id).get()
        if not wall.exists:
            raise HTTPException(400, {"error": "Wall not found"})
        return wall

    climbingLocation, secteur, user, wall = await asyncio.gather(check_cloc(), check_secteur(), check_user(), check_wall())
    user_dict = user.to_dict()
    wall_dict = wall.to_dict()
    secteur_dict = secteur.to_dict()
    user_ref = user.reference
    wall_ref = secteur_ref.collection("walls").document(wall_id)

    sentWalls = wall_dict.get("sentWalls", [])
    if user_id in sentwalls_ref_to_uids(sentWalls):
        raise HTTPException(400, {"error": "SentWall already exist"})

    # make sure user is subscribed to the gym topic, if not add it
    sub = list(user_dict.get("subscribed_topics", {}).keys())
    if climbingLocation_id not in sub:
        sub.append(climbingLocation_id)
        await user_ref.update({f"subscribed_topics.{climbingLocation_id}": True})

    # upload beta
    if beta and not beta_url:
        beta_url = await send_file_to_storage(beta, f"betaMedia/{climbingLocation_id}/{secteur_id}/{wall_id}/{beta.filename}", beta.content_type)
        # await async_updateSkillPlus(Skill.Video_Star, user_ref, 50)

        # get the gym account
        gyms = (
            firestore_async_db.collection("users")
            .where("isGym", "==", True)
            .where("climbingLocation_id", "==", cloc_ref)
            .stream()
        )
            
        async for gym in gyms:
            await handle_notif(
                "VIDEO",
                [user_dict.get("username")],
                [secteur_dict.get("newlabel")],
                dest_user=gym,
                climbingLocation_id=climbingLocation_id,
                secteur_id=secteur_id,
                wall_id=wall_id,
                user_id=user_id,
            )

    # if grade_id:
    #     await async_updateSkillPlus(Skill.Analytique_Averti, user_ref, 30)

    #remove projet if there is 
    projet = user_ref.collection("projects").where("wall_ref", "==", wall_ref).stream()
    async for p in projet:
        await p.reference.delete()

    grade = cloc_ref.collection("grades").document(grade_id) if grade_id else None

    data = {
        "beta": beta_url,
        "grade": grade,
        "nTentative": nTentative if nTentative else 0,
        "wall": wall_ref,
        "date": date if date else datetime.datetime.now(),
    }

    date, sentwall_ref = await user_ref.collection("sentWalls").add(data)
    await wall_ref.update({"sentWalls": firestore.ArrayUnion([sentwall_ref])})

    data["id"] = sentwall_ref.id
    data["wall"] = None
    data["date"] = data["date"].strftime("%Y-%m-%d %H:%M:%S")

    if data.get("grade"):
        grade = await data["grade"].get()
        grade_dict = grade.to_dict()
        grade_dict["id"] = grade.id
        data["grade"] = grade_dict

    user_tmp = user.to_dict()
    data["user"] = {
        "id": user_id,
        "username": user_tmp.get("username"),
        "profile_image_url": user_tmp.get("profile_image_url"),
    }

    # await update_user_points_single(doc_ref, [wall], user, True)
    # await vsl_sentwall_scoring(wall, ref, user_id, True)
    # await async_updateSkillPlus(Skill.Maitre_des_blocs, user_ref, 20)

    await asyncio.gather(
        update_user_points_single(cloc_ref, [wall], user, True),
        vsl_sentwall_scoring(wall, sentwall_ref, user_id, True),
        upload_sentwall_stats(sentwall_ref),
    )

    return data


@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/{wall_id}/sentwall/")
async def delete_sentwall(
    climbingLocation_id: str,
    secteur_id: str,
    wall_id: str,
    user_id: str = Depends(get_current_user),
):
    """probably cannot unsend an old wall, but that should be fine"""
    cloc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    wall_ref = cloc_ref.collection("secteurs").document(secteur_id).collection("walls").document(wall_id)

    async def check_user():
        user = await firestore_async_db.collection("users").document(user_id).get()
        if not user.exists:
            raise HTTPException(400, {"error": "User not found"})
        return user
    
    async def check_wall():
        wall = await wall_ref.get()
        if not wall.exists:
            raise HTTPException(400, {"error": "Wall not found"})
        return wall
    
    user, wall = await asyncio.gather(check_user(), check_wall())

    # check if there is a sentwall with the given wall_ref
    sentWalls = firestore_async_db.collection("users").document(user_id).collection("sentWalls").where("wall", "==", wall_ref).stream()

    async for sentWall in sentWalls:

        await asyncio.gather(
            sentWall.reference.delete(),
            wall_ref.update({"sentWalls": firestore.ArrayRemove([sentWall.reference])}),
            update_user_points_single(cloc_ref, [wall], user, False),
            vsl_sentwall_scoring(wall, sentWall.reference, user_id, False),
        )
        return {"message": "SentWall deleted successfully"}
    
    raise HTTPException(400, {"error": "SentWall not found"})

@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_id}/wall/{wall_id}/sentwall/{sentwall_id}/", response_model=SentWallResp)
async def patch_sentWall(
    climbingLocation_id: str,
    secteur_id: str,
    wall_id: str,
    sentwall_id: str,
    user_id: str = Depends(get_current_user),
    date: Optional[datetime.datetime] = Form(None),
    beta: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    nTentative: Optional[int] = Form(None),
):

    user, secteur, wall = await asyncio.gather(
        firestore_async_db.collection("users").document(user_id).get(),
        firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_id).get(),
        firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_id).collection("walls").document(wall_id).get(),
    )
    
    if not user.exists:
        raise HTTPException(400, {"error": "User not found"})

    if not secteur.exists:
        raise HTTPException(400, {"error": "Secteur not found"})
    
    if not wall.exists:
        raise HTTPException(400, {"error": "Wall not found"})
    

    user_dict = user.to_dict()
    secteur_dict = secteur.to_dict()
    wall_dict = wall.to_dict()

    sentWalls_ref = wall_dict.get("sentWalls", [])
    uids = sentwalls_ref_to_uids(sentWalls_ref)
    if user_id not in uids:
        raise HTTPException(400, {"error": "SentWall not found"})

    index = uids.index(user_id)
    sentWall_ref = sentWalls_ref[index]
    sentWall = await sentWall_ref.get()
    sentWall_dict: dict = sentWall.to_dict()

    to_update = {}

    # upload beta
    if beta and not beta_url:
        beta_url = await send_file_to_storage(beta, f"betaMedia/{climbingLocation_id}/{secteur_id}/{wall_id}/{beta.filename}", beta.content_type)
        # updateSkillPlus(Skill.Video_Star, firestore_db.collection("users").document(user_id), 50)

        gyms = (
            firestore_async_db.collection("users")
            .where("isGym", "==", True)
            .where("climbingLocation_id", "==", firestore_async_db.collection("climbingLocations").document(climbingLocation_id))
            .stream()
        )

        async for gym in gyms:
            await handle_notif(
                "VIDEO",
                [user_dict.get("username")],
                [secteur_dict.get("newlabel")],
                dest_user=gym,
                climbingLocation_id=climbingLocation_id,
                secteur_id=secteur_id,
                wall_id=wall_id,
                user_id=user_id,
            )
    if date:
        to_update["date"] = date

    if nTentative:
        to_update["nTentative"] = nTentative

    if grade_id:
        to_update["grade"] = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(grade_id)

    if beta_url:
        to_update["beta"] = beta_url

    if to_update:
        await sentWall_ref.update(to_update)

    sentWall_dict.update(to_update)
    sentWall_dict["id"] = sentWall_ref.id
    sentWall_dict["wall"] = None
    sentWall_dict["date"] = sentWall_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    if sentWall_dict["grade"]:
        grade = await sentWall_dict["grade"].get()
        sentWall_dict["grade"] = grade.to_dict()
        sentWall_dict["grade"]["id"] = grade.id

    sentWall_dict["user"] = {
        "id": user_id,
        "username": user_dict.get("username"),
        "profile_image_url": user_dict.get("profile_image_url"),
    }

    return sentWall_dict

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/secteur/{secteur_ref}/wall/{wall_ref}/sentwall/{sentwall_ref}/")
async def delete_sentit(
    climbingLocation_id: str,
    secteur_ref: str,
    wall_ref: str,
    sentwall_ref: str,
    user_id: str = Depends(get_current_user),
):
    async def check_cloc():
        climbingLocation = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).get()
        if not climbingLocation.exists:
            raise HTTPException(400, {"error": "ClimbingLocation not found"})
        return climbingLocation
    
    async def check_secteur():
        secteur = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("secteurs").document(secteur_ref).get()
        if not secteur.exists:
            raise HTTPException(400, {"error": "Secteur not found"})
        return secteur

    async def check_sentWall():
        sentWall = await firestore_async_db.collection("users").document(user_id).collection("sentWalls").document(sentwall_ref).get()
        if not sentWall.exists:
            raise HTTPException(400, {"error": "SentWall not found"})
        return sentWall
    
    async def get_user():
        return await firestore_async_db.collection("users").document(user_id).get()
    
    climbingLocation, secteur, sentWall, user = await asyncio.gather(check_cloc(), check_secteur(), check_sentWall(), get_user())
    sentWall_ref = sentWall.reference

    wall_ref = secteur.reference.collection("walls").document(wall_ref)
    wall = await wall_ref.get()

    await asyncio.gather(
        sentWall_ref.delete(),
        wall_ref.update({"sentWalls": firestore.ArrayRemove([sentWall_ref])}),
        update_user_points_single(climbingLocation.reference, [wall], user, False),
        vsl_sentwall_scoring(wall, sentWall_ref, user_id, False),
    )

    # await async_updateSkillLess(Skill.Maitre_des_blocs, user.reference, 20)
    # await async_updateSkillLess(Skill.Video_Star, user.reference, 50)

    return {"message": "SentWall deleted successfully"}


# # Sent Multiple Wall at the same time
# @app.post("/api/v1/climbingLocation/{climbingLocation_id}/sentwall/")
# async def create_sentwalls_list(
#     climbingLocation_id: str,
#     sentwalls: ListSentWall = Form(...),
#     uid: str = Depends(get_current_user)
# ):
#     # Fetch climbingLocation asynchronously
#     climbingLocation_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
#     climbingLocation = await climbingLocation_ref.get()
#     if not climbingLocation.exists:
#         raise HTTPException(400, {"error": "ClimbingLocation not found"})

#     listSentWalls = sentwalls.sentwalls
#     user_ref = firestore_async_db.collection("users").document(uid)
#     user = await user_ref.get()
#     sectors = await climbingLocation_ref.collection("secteurs").get()

#     all_walls = []

#     async def process_sentwall(sentwall):
#         possible_refs = [secteur.reference.collection("walls").document(sentwall.id) for secteur in sectors]
#         possible_walls = firestore_async_db.get_all(possible_refs)
#         walls = [wall async for wall in possible_walls if wall.exists]
#         if len(walls) == 0:
#             return None

#         wall = walls[0]

#         # SentWall already exists
#         existing_sentwalls = await (
#             user_ref.collection("sentWalls")
#             .where("wall", "==", wall.reference)
#             .limit(1)
#             .get()
#         )

#         if len(existing_sentwalls) > 0:
#             return None  

#         await async_updateSkillPlus(Skill.Maitre_des_blocs, user_ref, 20)

#         grade_ref = (
#             climbingLocation_ref.collection("grades").document(sentwall.grade_id)
#             if sentwall.grade_id
#             else None
#         )

#         data = {
#             "beta": None,
#             "grade": grade_ref,
#             "nTentative": sentwall.nTentative if sentwall.nTentative else 0,
#             "wall": wall.reference,
#             "date": datetime.datetime.now(),
#         }

#         _, newsentwall = await user_ref.collection("sentWalls").add(data)
#         data["id"] = newsentwall.id
#         all_walls.append(wall)

#     await asyncio.gather(*(process_sentwall(sentwall) for sentwall in listSentWalls))
#     await update_user_points_single(climbingLocation_ref, all_walls, user, True)

#     return {"message": "SentWalls created successfully"}