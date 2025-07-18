import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from fastapi import Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from google.cloud import firestore

from ..settings import (
    BUCKET_NAME,
    app,
    firestore_async_db,
    firestore_db,
    storage_client,
)
from ..User.deps import get_current_user
from ..utils import send_file_to_storage
from .models import NewsResp
from .utils import (
    handle_notif,
    process_notif,
    resend_notification_topic,
    send_notification_topic,
    send_notification_user,
    construct_notif,
    LANGUAGES,
    SUBTOPICS,
)


@app.post("/api/v1/news/{topic_id}/", response_model=NewsResp)
async def create_news(
    topic_id: str,
    news_type: str = Form("NEWS"),
    title: str = Form(""),
    description: str = Form(""),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    user = await user_ref.get()
    user_dict = user.to_dict()
    if not user_dict:
        raise HTTPException(400, {"error": "User not found"})

    lang = user_dict.get("lang", "fr")

    if not image_url and image:
        image_url = await send_file_to_storage(
            image, f"news/{topic_id}/{image.filename}", image.content_type
        )

    ret = await handle_notif(
        news_type,
        [title],
        [description],
        notif_topic=topic_id,
        image_url=image_url,
        url=url,
    )

    if not ret:
        raise HTTPException(400, {"error": "Could not create news"})

    created_news = await firestore_async_db.collection("News").document(topic_id).collection("news").document(ret["id"]).get()
    news_dict = process_notif(created_news, lang)
    return news_dict


@app.post("/api/v1/climbingLocation/{climbingLocation_id}/news/")
async def create_climbingLocation_news(
    climbingLocation_id: str,
    title: str = Form(...),
    description: str = Form(...),
    image: Optional[UploadFile] = File(...),
    image_url: Optional[str] = Form(None),
    uid: str = Depends(get_current_user),
):
    return await create_news(climbingLocation_id, "NEWS", title, description, image, image_url, None, uid)


@app.get("/api/v1/news/{topic_id}/", response_model=List[NewsResp])
async def list_topic(
    topic_id: str,
    lang: Optional[str] = None,
    limit: Optional[int] = 10,
    start_after_date: Optional[str] = None,
):
    news = []
    query = (
        firestore_async_db.collection("News")
        .document(topic_id)
        .collection("news")
        .order_by("date", direction=firestore.Query.DESCENDING)
    )
    if start_after_date:
        start_after = datetime.datetime.fromisoformat(start_after_date)
        query = query.where("date", "<", start_after)

    query = query.limit(limit)

    docs = query.stream()
    async for doc in docs:
        dict_doc = process_notif(doc, lang)
        news.append(dict_doc)

    return news


@app.get("/api/v1/news/{topic_id}/{news_id}", response_model=NewsResp)
async def get_news(
    topic_id: str,
    news_id: Optional[str] = None,
    lang: Optional[str] = None,
):
    # fetch a specific news
    doc_ref = (
        firestore_async_db.collection("News")
        .document(topic_id)
        .collection("news")
        .document(news_id)
    )
    doc = await doc_ref.get()
    if not doc.exists:
        raise HTTPException(404, {"error": "News not found"})

    dict_doc = doc.to_dict()
    dict_doc["id"] = doc.id
    return dict_doc


@app.patch("/api/v1/news/{topic_id}/{news_id}/", response_model=NewsResp)
async def patch_news(
    topic_id: str,
    news_id: str,
    title: str = Form(None),
    description: str = Form(None),
    date: str = Form(None),
    image: Optional[UploadFile] = File(None),
    uid: dict = Depends(get_current_user),
):
    news_ref = (
        firestore_async_db.collection("News")
        .document(topic_id)
        .collection("news")
        .document(news_id)
    )
    news = await news_ref.get()
    if not news.exists:
        raise HTTPException(404, {"error": "News not found"})

    if image:
        image_url = await send_file_to_storage(
            image, f"news/{topic_id}/{image.filename}", image.content_type
        )

    to_update = {}
    if title:
        to_update["title"] = title
    if description:
        to_update["description"] = description
    if image:
        to_update["image_url"] = image_url

    if to_update:
        to_update["date"] = datetime.datetime.now() if not date else date
        await news_ref.update(to_update)

    news = await news_ref.get()
    news_dict = news.to_dict()
    news_dict["id"] = news.id
    return news_dict


@app.delete("/api/v1/news/{topic_id}/{news_id}/")
async def delete_news(
    topic_id: str,
    news_id: str,
    uid: dict = Depends(get_current_user),
):
    doc_ref = (
        firestore_async_db.collection("News")
        .document(topic_id)
        .collection("news")
        .document(news_id)
    )
    doc = await doc_ref.get()
    if not doc.exists:
        raise HTTPException(404, {"error": "News not found"})

    await doc_ref.delete()
    return {"message": "News deleted successfully"}


@app.post("/api/v1/news/{topic_id}/{news_id}/")
async def resend_news(
    topic_id: str,
    news_id: str,
    uid: dict = Depends(get_current_user),
):
    doc_ref = (
        firestore_async_db.collection("News")
        .document(topic_id)
        .collection("news")
        .document(news_id)
    )
    doc = await doc_ref.get()
    if not doc.exists:
        raise HTTPException(404, {"error": "News not found"})

    news = doc.to_dict()
    news["id"] = news_id

    date = news.get(
        "date", datetime.datetime.now(datetime.timezone.utc)
    )  # just in case ? but should not happen
    now = datetime.datetime.now(datetime.timezone.utc)
    if (now - date).days < 1:
        raise HTTPException(400, {"error": "News already sent today"})
    
    # Update last sent date
    doc_ref.update({"date": now})
    await resend_notification_topic(news)
    return news


@app.get("/api/v1/user/news/", response_model=List[NewsResp])
async def get_user_news(
    limit: int = 10,
    start_after_date: Optional[str] = None,
    uid: str = Depends(get_current_user),
):
    return []


@app.get("/api/v2/user/news/", response_model=List[NewsResp])
async def get_user_news(
    limit: int = 10,
    start_after_date: Optional[str] = None,
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    user = await user_ref.get()
    user_dict = user.to_dict()

    if not user_dict:
        raise HTTPException(400, {"error": "User not found"})

    # get the last date the user saw the news
    last_date_news = user_dict.get("lastDateNews", datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc))

    topics = user_dict.get("subscribed_topics", {})
    subscribed_topics = [sub for sub in topics if topics[sub]]
    # subscribed_subtopics = user_dict.get("subscribed_subtopics", SUBTOPICS)

    # add gym topic if user is a gym
    isGym = user_dict.get("isGym", False)
    if isGym:
        cloc_id = user_dict.get("climbingLocation_id").id
        subscribed_topics.append(cloc_id)

    # add defaults to subscribed topics
    defaults = ["VS", "VSL", uid]
    for default in defaults:
        if default not in subscribed_topics:
            subscribed_topics.append(default)

    # get lang preferences
    lang = user_dict.get("lang", "fr")
    if lang not in LANGUAGES:
        lang = "fr"

    news = []
    query = (
        firestore_async_db.collection_group("news")
        .where("topic", "in", subscribed_topics)
        # .where("news_type", "in", subscribed_subtopics)
        .order_by("date", direction=firestore.Query.DESCENDING)
    )
    if start_after_date:
        start_after = datetime.datetime.fromisoformat(start_after_date)
        query = query.where("date", "<", start_after)

    query = query.limit(limit)
    docs = query.stream()
    async for doc in docs:
        dict_doc = process_notif(doc, lang)

        if "date" in dict_doc and dict_doc["date"] < last_date_news:
            dict_doc["is_read"] = True

        news.append(dict_doc)

    return news


@app.patch("/api/v1/user/news/", response_model=Dict[str, str])
async def update_user_last_news_date(
    uid: str = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    user = await user_ref.get()
    user_dict = user.to_dict()
    if not user_dict:
        raise HTTPException(400, {"error": "User not found"})

    await user_ref.update({"lastDateNews": datetime.datetime.now()})
    return {"message": "User last news date updated"}


@app.post("/api/v1/user/news/", response_model=NewsResp)
async def debug_send_notif_to_user(
    news_type: str = Form(...),
    title_params: str = Form(...),
    body_params: str = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    uid: str = Form(...),
    url: Optional[str] = Form(None),
    my_uid: dict = Depends(get_current_user),
):
    user_ref = firestore_async_db.collection("users").document(uid)
    user = await user_ref.get()
    user_dict = user.to_dict()
    lang = user_dict.get("lang", "fr")
    fcm_token = user_dict.get("fcm_token")

    if not image_url and image:
        image_url = await send_file_to_storage(
            image, f"news/{uid}/{image.filename}", image.content_type
        )

    title_params = title_params.split("|")
    body_params = body_params.split("|")

    title, body = construct_notif(lang, news_type, title_params, body_params)
    if not title or not body:
        raise HTTPException(400, {"error": "Invalid notif type"})
    
    ret = await handle_notif(
        news_type,
        title_params,
        body_params,
        dest_user=user,
        image_url=image_url,
        url=url,
    )

    if not ret:
        raise HTTPException(400, {"error": "Could not create news"})
    
    title, body = construct_notif(lang, news_type, title_params, body_params)
    ret["title"] = title
    ret["description"] = body
    return ret

@app.get("/api/v1/climbingLocation/{climbingLocation_id}/news/")
async def get_climbingLocation_news(
    climbingLocation_id: str,
    news_id: Optional[str] = None
):
    # here the language doesn't matter because the news are not translated

    if news_id:
        doc = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("news").document(news_id).get()
        if not doc.exists:
            doc = await firestore_async_db.collection("News").document(climbingLocation_id).collection("news").document(news_id).get()
            dict_doc = doc.to_dict()
            dict_doc["id"] = doc.id
            dict_doc["title"], dict_doc["description"] = construct_notif("fr", dict_doc["news_type"], dict_doc["title_payload"], dict_doc["body_payload"])
            return dict_doc

        dict_doc = doc.to_dict()
        dict_doc["id"] = doc.id
        return dict_doc
    
    # fetch all news
    
    news = []
    new_docs = firestore_async_db.collection("News").document(climbingLocation_id).collection("news").where("news_type", "==", "NEWS").stream()
    async for doc in new_docs:
        dict_doc = doc.to_dict()
        dict_doc["id"] = doc.id
        dict_doc["title"], dict_doc["description"] = construct_notif("fr", dict_doc["news_type"], dict_doc["title_payload"], dict_doc["body_payload"])
        news.append(dict_doc)

    old_docs = firestore_async_db.collection("climbingLocations").document(climbingLocation_id).collection("news").stream()
    async for doc in old_docs:
        dict_doc = doc.to_dict()
        dict_doc["id"] = doc.id
        news.append(dict_doc)

    for n in news:
        # make up an old date if not present
        if "date" not in n:
            n["date"] = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

        # convert str dates to datetime
        if isinstance(n["date"], str):
            n["date"] = datetime.datetime.fromisoformat(n["date"])

        n["date"] = n["date"].replace(tzinfo=datetime.timezone.utc)

    news = sorted(news, key=lambda x: x["date"], reverse=True)
    return news
