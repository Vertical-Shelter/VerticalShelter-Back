import asyncio
import datetime
from typing import List, Optional

from fastapi import Body, Depends, File, Form, HTTPException, UploadFile
from google.cloud import firestore

from app.Wall.models import SentWallResp

from ..settings import BUCKET_NAME, app, firestore_async_db, storage_client
from ..User.deps import get_current_user
from ..User.utils import get_user_mini
from ..Stats.utils import upload_sentwall_stats
from ..Wall.models import WallResp, LikeResp, CommentResp
from ..Wall.utils import calculate_points, get_grade, sentwalls_ref_to_uids
from .models import Annotation, Annotations, SprayWallBloc, SprayWallResp
from .utils import get_likes, get_comments


@app.get("/api/v1/climbingLocation/spraywalls/", response_model=List[SprayWallResp])
async def list_all_spraywalls(
    annotations: Optional[bool] = None,
    uid: str = Depends(get_current_user),
):
    spraywalls = firestore_async_db.collection_group("spraywalls").stream()
    spraywalls_list = []

    async for spraywall in spraywalls:
        spraywall_dict = spraywall.to_dict()
        spraywall_dict["id"] = spraywall.id
        spraywall_dict["climbingLocation_id"] = spraywall.reference.parent.parent.id

        if annotations is None:
            spraywalls_list.append(spraywall_dict)
            continue

        anns = spraywall_dict.get("annotations")
        if annotations and anns:
            spraywalls_list.append(spraywall_dict)
        elif not annotations and not anns:
            spraywalls_list.append(spraywall_dict)

    return spraywalls_list

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/", response_model=List[SprayWallResp])
async def get_spraywalls(
    climbingLocation_id: str,
    uid: str = Depends(get_current_user),
):
    date = datetime.datetime.now()
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywalls = doc_ref.collection("spraywalls").stream()
    spraywalls_list = []

    async for spraywall in spraywalls:
        spraywall_dict = spraywall.to_dict()
        spraywall_dict["id"] = spraywall.id
        spraywall_dict["climbingLocation_id"] = climbingLocation_id

        # remove annotations to avoid sending them in response
        # anns = spraywall_dict.pop("annotations", None)

        # if annotations is None:
        #     spraywalls_list.append(spraywall_dict)
        #     continue

        # if annotations and anns:
        #     spraywalls_list.append(spraywall_dict)
        # elif not annotations and not anns:
        spraywalls_list.append(spraywall_dict)
    return spraywalls_list


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}", response_model=SprayWallResp)
async def get_spraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall = doc_ref.collection("spraywalls").document(spraywall_id)
    spraywall_dict = (await spraywall.get()).to_dict()
    if not spraywall_dict:
        raise HTTPException(status_code=404, detail="Spraywall not found")

    spraywall_dict["id"] = spraywall.id
    spraywall_dict["climbingLocation_id"] = climbingLocation_id
    return spraywall_dict


@app.get("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/label/{label}", response_model=SprayWallResp)
async def get_spraywall_by_name(
    climbingLocation_id: str,
    label: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywalls = doc_ref.collection("spraywalls").where("label", "==", label).limit(1).stream()

    async for spraywall in spraywalls:
        spraywall_dict = spraywall.to_dict()
        spraywall_dict["id"] = spraywall.id
        spraywall_dict["climbingLocation_id"] = climbingLocation_id
        return spraywall_dict
    
    raise HTTPException(status_code=404, detail="Spraywall not found")


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/", response_model=SprayWallResp)
async def create_spraywall(
    climbingLocation_id: str,
    annotations: Optional[List[Annotation]] = [],
    image: UploadFile = File(...),
    label: str = Form(...),
    uid: str = Depends(get_current_user),
):
    # TODO: if no annotations, send an email / notification for manual review and annotation

    # upload image to storage
    blob = storage_client.bucket(BUCKET_NAME).blob(f"spraywalls/{climbingLocation_id}/{image.filename}")
    blob.upload_from_file(image.file, content_type=image.content_type)
    blob.make_public()


    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    _, ret = await doc_ref.collection("spraywalls").add({
        "label": label,
        "image": blob.public_url,
        "annotations": annotations,
    })

    return {
        "label": label,
        "image": blob.public_url,
        "annotations": annotations,
        "id": ret.id,
    }

# TODO: migrate

@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/", response_model=SprayWallResp)
async def update_spraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    annotations: Optional[Annotations] = Form(None),
    image: Optional[UploadFile] = File(None),
    label: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)

    to_update = {}

    if image:
        old_image_url = (await spraywall_ref.get()).to_dict().get("image")
        if old_image_url:
            old_image_path = old_image_url.split(f"https://storage.googleapis.com/{BUCKET_NAME}/")[1]
            storage_client.bucket(BUCKET_NAME).blob(old_image_path).delete()

        # upload new image to storage, delete old image
        blob = storage_client.bucket(BUCKET_NAME).blob(f"spraywalls/{climbingLocation_id}/{image.filename}")
        blob.upload_from_file(image.file, content_type=image.content_type)
        blob.make_public()
        to_update["image"] = blob.public_url

    if annotations:
        annotations_list = [annotation.model_dump() for annotation in annotations.annotations]
        to_update["annotations"] = annotations_list

    if label:
        to_update["label"] = label

    await spraywall_ref.update(to_update)
    spraywall_dict = (await spraywall_ref.get()).to_dict()
    spraywall_dict["id"] = spraywall_ref.id
    return spraywall_dict

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}")
async def delete_spraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)

    await spraywall_ref.delete()
    return {"message": "Spraywall deleted successfully"}

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/", response_model=WallResp)
async def create_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    spraywall_bloc: SprayWallBloc = Form(...),
    betaOuvreur: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)

    dump = spraywall_bloc.model_dump()
    dump["routesetter"] = user_ref
    dump["date"] = datetime.datetime.now()
    dump["sentWalls"] = []
    # ensure grade_id exists
    grade = await doc_ref.collection("grades").document(dump.get("grade_id")).get()
    if not grade.exists:
        raise HTTPException(status_code=404, detail="Grade not found")

    _, ref = await spraywall_ref.collection("blocs").add(dump)
    bloc_id = ref.id

    if betaOuvreur and not beta_url:
        blob = storage_client.bucket(BUCKET_NAME).blob(f"betaMedia/{climbingLocation_id}/{spraywall_id}/{bloc_id}/{betaOuvreur.filename}")
        blob.upload_from_file(betaOuvreur.file, content_type=betaOuvreur.content_type)
        blob.make_public()
        dump["betaOuvreur"] = blob.public_url
        await ref.update({"betaOuvreur": blob.public_url})
    elif beta_url:
        dump["betaOuvreur"] = beta_url
        await ref.update({"betaOuvreur": beta_url})

    dump.update({"id": bloc_id, "grade_id": grade.id})
    return dump

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/", response_model=List[WallResp])
async def get_spraywall_blocs(
    climbingLocation_id: str,
    spraywall_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    blocs = spraywall_ref.collection("blocs").stream()

    async def process_bloc(bloc):
        bloc_dict = bloc.to_dict()
        bloc_dict["id"] = bloc.id
        bloc_dict["isDone"] = uid in sentwalls_ref_to_uids(bloc_dict.get("sentWalls", []))

        if not bloc_dict.get("betaOuvreur"):
            some_beta = firestore_async_db.collection_group("sentWalls").where("wall", "==", bloc.reference).where("beta", ">=", "").limit(1).stream()
            async for beta in some_beta:
                bloc_dict["betaOuvreur"] = beta.to_dict()["beta"]
                break
 
        return bloc_dict

    blocs_list = await asyncio.gather(*[process_bloc(bloc) async for bloc in blocs])

    return blocs_list

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}", response_model=WallResp)
async def get_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)

    bloc_dict = (await bloc_ref.get()).to_dict()
    bloc_dict["id"] = bloc_ref.id
    grade_id = bloc_dict.get("grade_id")
    sprayWall_refs = bloc_dict.get("sentWalls", [])

    routesetter, likes, comments, grade = await asyncio.gather(
        get_user_mini(bloc_dict.get("routesetter")),
        asyncio.gather(*[get_likes(like_ref) async for like_ref in bloc_ref.collection("likes").stream()]),
        asyncio.gather(*[get_comments(comment_ref) async for comment_ref in bloc_ref.collection("comments").stream()]),
        doc_ref.collection("grades").document(grade_id).get(),
    )

    grade_dict = grade.to_dict()

    # add id to sentwalls
    sentWalls_list = []
    async def process_sentwall(sentWall):
        sentWall_dict = sentWall.to_dict()
        user_ref = sentWall.reference.parent.parent
        sentWall_dict["id"] = sentWall.id
        sentWall_dict["user"] = await get_user_mini(user_ref)

        # if user is the current user, add the grade
        if sentWall_dict["user"]["id"] == uid:
            sentWall_dict["grade"] = await get_grade(sentWall_dict.get("grade"))
        else:
            sentWall_dict.pop("grade", None)

        sentWalls_list.append(sentWall_dict)
    await asyncio.gather(*[process_sentwall(sentWall) async for sentWall in firestore_async_db.get_all(sprayWall_refs)])

    bloc_dict["sentWalls"] = sentWalls_list
    bloc_dict["routesetter"] = routesetter 
    bloc_dict["likes"] = likes
    bloc_dict["comments"] = comments
    bloc_dict["points"] = await calculate_points(grade_dict.get("vgrade"), climbingLocation_id)
    bloc_dict["isDone"] = uid in sentwalls_ref_to_uids(sprayWall_refs)

    return bloc_dict

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}")
async def delete_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)

    await bloc_ref.delete()
    return {"message": "Bloc deleted successfully"}

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/sentwall/", response_model=SentWallResp)
async def create_sentspraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    grade_id: str = Form(None),
    nTentative: int = Form(0),
    beta: Optional[UploadFile] = File(None),
    grade_font: Optional[str] = Form(None),
    beta_url: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)
    grade_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(grade_id)

    if beta and not beta_url:
        blob = storage_client.bucket(BUCKET_NAME).blob(f"betaMedia/{climbingLocation_id}/{spraywall_id}/{bloc_id}/{beta.filename}")
        blob.upload_from_file(beta.file, content_type=beta.content_type)
        blob.make_public()
        beta_url = blob.public_url

    sentWall_dict = {
        "grade": grade_ref,
        "climbingLocation_id": climbingLocation_id,
        "nTentative": nTentative,
        "beta": beta_url,
        "date": datetime.datetime.now(),
        "wall": bloc_ref,
        "grade_font": grade_font,
    }

    _, ref = await user_ref.collection("sentWalls").add(sentWall_dict)
    await bloc_ref.update({"sentWalls": firestore.ArrayUnion([ref])})

    # TODO: add score to user

    await upload_sentwall_stats(ref)

    resDict = sentWall_dict
    resDict.update({"id": ref.id})
    resDict["date"] = resDict["date"].strftime("%Y-%m-%d %H:%M:%S")
    resDict["user"] = await get_user_mini(user_ref)

    grade_dict = (await grade_ref.get()).to_dict()
    if grade_dict:
        grade_dict["id"] = grade_ref.id
    resDict["grade"] = grade_dict

    return resDict

@app.patch("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/sentwall/", response_model=SentWallResp)
async def update_sentspraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    grade_id: str = Form(None),
    nTentative: int = Form(None),
    beta: Optional[UploadFile] = File(None),
    beta_url: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)
    grade_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("grades").document(grade_id)

    sentwalls = await user_ref.collection("sentWalls").where("wall", "==", bloc_ref).get()
    if len(sentwalls) == 0:
        raise HTTPException(status_code=400, detail="SentWall not found")
    
    sentwall = sentwalls[0]
    sentwall_ref = sentwall.reference
    sentwall_dict = sentwall.to_dict()

    to_update = {}
    if grade_id:
        to_update["grade"] = grade_ref
    if nTentative:
        to_update["nTentative"] = nTentative
    if beta and not beta_url:
        blob = storage_client.bucket(BUCKET_NAME).blob(f"betaMedia/{climbingLocation_id}/{spraywall_id}/{bloc_id}/{beta.filename}")
        blob.upload_from_file(beta.file, content_type=beta.content_type)
        blob.make_public()
        to_update["beta"] = blob.public_url
    elif beta_url:
        to_update["beta"] = beta_url

    await sentwall_ref.update(to_update)
    sentwall_dict.update(to_update)
    sentwall_dict["id"] = sentwall_ref.id
    sentwall_dict["user"] = await get_user_mini(user_ref)

    grade_dict = (await grade_ref.get()).to_dict()
    if grade_dict:
        grade_dict["id"] = grade_ref.id
    sentwall_dict["grade"] = grade_dict

    return sentwall_dict

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/sentwall/")
async def delete_sentspraywall(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)

    # check if user has already sent
    async for sentwall in user_ref.collection("sentWalls").stream():
        sentwall_ref = sentwall.reference

    sentwalls = await user_ref.collection("sentWalls").where("wall", "==", bloc_ref).get()
    if len(sentwalls) == 0:
        raise HTTPException(status_code=400, detail="SentWall not found")
    
    sentwall_ref = sentwalls[0].reference
    await bloc_ref.update({"sentWalls": firestore.ArrayRemove([sentwall_ref])})
    await sentwall_ref.delete()

    return {"message": "SentWall deleted successfully"}

# TODO: update beta

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/likes/", response_model=LikeResp | dict)
async def like_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)
    likes_collection = bloc_ref.collection("likes")

    # check if user has already liked
    likes = await likes_collection.where("user", "==", firestore_async_db.collection("users").document(uid)).get()
    if len(likes) > 0:
        await likes[0].reference.delete()
        return {"message": "Like deleted successfully"}

    user_ref = firestore_async_db.collection("users").document(uid)
    like_dict = {
        "user": user_ref,
        "date": datetime.datetime.now(),
    }

    _, ref = await likes_collection.add(like_dict)
    like_id = ref.id

    like_dict.update({"id": like_id})
    like_dict["date"] = like_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    like_dict["user"] = (await user_ref.get()).to_dict()
    like_dict["user"]["id"] = uid
    return LikeResp(**like_dict)

@app.post("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/comments/", response_model=CommentResp)
async def comment_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    comment: str = Form(...),
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)
    comments_collection = bloc_ref.collection("comments")
    user_ref = firestore_async_db.collection("users").document(uid)
    comment_dict = {
        "user": user_ref,
        "comment": comment,
        "date": datetime.datetime.now(),
    }

    _, ref = await comments_collection.add(comment_dict)
    comment_id = ref.id

    comment_dict.update({"id": comment_id})
    comment_dict["date"] = comment_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    comment_dict["user"] = (await user_ref.get()).to_dict()
    comment_dict["user"]["id"] = uid
    return comment_dict

@app.delete("/api/v1/climbingLocation/{climbingLocation_id}/spraywalls/{spraywall_id}/blocs/{bloc_id}/comments/{comment_id}")
async def delete_comment_spraywall_bloc(
    climbingLocation_id: str,
    spraywall_id: str,
    bloc_id: str,
    comment_id: str,
    uid: str = Depends(get_current_user),
):
    doc_ref = firestore_async_db.collection("climbingLocations").document(climbingLocation_id)
    spraywall_ref = doc_ref.collection("spraywalls").document(spraywall_id)
    bloc_ref = spraywall_ref.collection("blocs").document(bloc_id)
    comment_ref = bloc_ref.collection("comments").document(comment_id)

    comment = await comment_ref.get()
    comment_dict = comment.to_dict()
    if not comment.exists:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment_dict.get("user").id != uid:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this comment (how did you get here?)")

    await comment_ref.delete()
    return {"message": "Comment deleted successfully"}

# TODO: how to handle bloc deletion / bloc_id change ? 

