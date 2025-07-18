from fastapi import FastAPI, Form, HTTPException, Depends, File, UploadFile
from ..news.utils import send_invite_to_user, send_friend_accepted_to_user
from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from .utils import *
from .deps import get_current_user

# Friends
@app.post("/api/v1/user/{dest_user_id}/add-friend/")
async def ask_friend(dest_user_id: str, uid: dict = Depends(get_current_user)):
    # check if user exists
    user = firestore_db.collection("users").document(dest_user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})
    else:
        # check if friend request already exists
        list_user1 = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(uid))
            .get()
        )
        if len(list_user1) > 0:
            raise HTTPException(400, {"error": "Friend request already sent"})
        firestore_db.collection("users").document(dest_user_id).collection("friend_request").add(
            {
                "user_id": firestore_db.collection("users").document(uid),
                "status": "PENDING",
                "date": datetime.now(),
            }
        )
        firestore_db.collection("users").document(uid).collection("friend_request").add(
            {
                "user_id": firestore_db.collection("users").document(dest_user_id),
                "status": "REQUESTED",
                "date": datetime.now(),
            }
        )

        await send_invite_to_user(uid, dest_user_id)
        return {"message": "Friend request sent successfully"}


@app.post("/api/v1/user/{dest_user_id}/cancel-friend/")
def cancel_friendRequest(dest_user_id: str, uid: dict = Depends(get_current_user)):
    # check if user exists
    user = firestore_db.collection("users").document(dest_user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})
    else:
        list_user1 = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(uid))
            .get()
        )
        for user1 in list_user1:
            user1.reference.delete()

        list_user2 = (
            firestore_db.collection("users")
            .document(uid)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(dest_user_id))
            .get()
        )
        for user2 in list_user2:
            user2.reference.delete()
        # delete friend news
        list_fq = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(uid))
            .where("friends_type", "==", "NEW_FRIEND")
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()
        list_fq = (
            firestore_db.collection("users")
            .document(uid)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(dest_user_id))
            .where("friends_type", "==", "NEW_FRIEND")
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()
        return {"message": "Friend request canceled successfully"}


@app.post("/api/v1/user/{dest_user_id}/delete-friend/")
def delete_friend(dest_user_id: str, uid: dict = Depends(get_current_user)):
    # check if user exists
    user = firestore_db.collection("users").document(dest_user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})
    else:
        list_user1 = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("friends")
            .where("user_id", "==", firestore_db.collection("users").document(uid))
            .get()
        )
        for user1 in list_user1:
            user1.reference.delete()

        list_user2 = (
            firestore_db.collection("users")
            .document(uid)
            .collection("friends")
            .where("user_id", "==", firestore_db.collection("users").document(dest_user_id))
            .get()
        )
        for user2 in list_user2:
            user2.reference.delete()
        list_fq = (
            firestore_db.collection("users")
            .document(uid)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(dest_user_id))
            .where("friends_type", "==", "FRIEND_ACCEPTED")
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()
        list_fq = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(uid))
            .where("friends_type", "==", "FRIEND_ACCEPTED")
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()

        return {"message": "Friend deleted successfully"}


@app.post("/api/v1/user/{dest_user_id}/accept-friend/")
async def accept_friend(dest_user_id: str, uid: dict = Depends(get_current_user)):
    # check if user exists
    user = firestore_db.collection("users").document(dest_user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})

    firestore_db.collection("users").document(uid).collection("friends").document(dest_user_id).set(
        {
            "user_id": firestore_db.collection("users").document(dest_user_id),
        }
    )
    firestore_db.collection("users").document(dest_user_id).collection("friends").document(uid).set(
        {
            "user_id": firestore_db.collection("users").document(uid),
        }
    )
    list_fq = (
        firestore_db.collection("users")
        .document(dest_user_id)
        .collection("friend_request")
        .where("user_id", "==", firestore_db.collection("users").document(uid))
        .get()
    )
    for fq in list_fq:
        fq.reference.delete()

    list_fq2 = (
        firestore_db.collection("users")
        .document(uid)
        .collection("friend_request")
        .where("user_id", "==", firestore_db.collection("users").document(dest_user_id))
        .get()
    )
    for fq2 in list_fq2:
        fq2.reference.delete()

    # try:
    #     await update_user_news(
    #         UserNews(
    #             newsType="Friends",
    #             friend_id=user_id,
    #             friends_type="FRIEND_ACCEPTED",
    #         ),
    #         my_id=uid,
    #     )
    # except Exception as e:
    #     print(e)

    await send_friend_accepted_to_user(uid, dest_user_id)

    return {"message": "Friend added successfully"}


@app.get("/api/v1/user/me/friend-request/")
def list_friend_req(user_id: dict = Depends(get_current_user)):
    user_friends_stream = firestore_db.collection("users").document(user_id).collection("friend_request").stream()
    list_user_friends_stream = list(user_friends_stream)
    list_res = []
    for ufr in list_user_friends_stream:
        ufr_dict = ufr.to_dict()
        if "status" in ufr_dict and ufr_dict["status"] == "PENDING":
            user = ufr_dict["user_id"].get()

            if not user.exists:
                continue

            user_dict = {
                "id": user.id,
                "username": user.to_dict()["username"],
                "profile_image_url": user.to_dict()["profile_image_url"] if "profile_image_url" in user.to_dict() else "",
            }
            list_res.append(user_dict)
    return list_res


@app.post("/api/v1/user/{dest_user_id}/refuse-friend/")
def refuse_friend(dest_user_id: str, uid: dict = Depends(get_current_user)):

    # check if user exists
    user = firestore_db.collection("users").document(dest_user_id).get().to_dict()
    if user == None:
        raise HTTPException(400, {"error": "User not found"})
    else:
        list_fq = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(uid))
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()

        list_fq2 = (
            firestore_db.collection("users")
            .document(uid)
            .collection("friend_request")
            .where("user_id", "==", firestore_db.collection("users").document(dest_user_id))
            .get()
        )
        for fq2 in list_fq2:
            fq2.reference.delete()
        list_fq = (
            firestore_db.collection("users")
            .document(dest_user_id)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(uid))
            .where("friends_type", "==", "NEW_FRIEND")
            .get()
        )

        for fq in list_fq:
            fq.reference.delete()
        list_fq = (
            firestore_db.collection("users")
            .document(uid)
            .collection("news")
            .where("friend_id", "==", firestore_db.collection("users").document(dest_user_id))
            .where("friends_type", "==", "NEW_FRIEND")
            .get()
        )
        for fq in list_fq:
            fq.reference.delete()

        return {"message": "Friend request refused successfully"}
