from ...settings import firestore_db, storage_client, BUCKET_NAME, app
from fastapi import Depends, File, UploadFile, Form
from fastapi.exceptions import HTTPException
from typing import Optional, List, Union
from ...User.deps import get_current_user
from datetime import datetime, timedelta
from google.cloud import firestore
from ..Quetes.models import *


# Create quete
@app.post("/api/v1/season_pass/{season_pass_id}/quetes_quotidienne/", response_model=QueteReturn)
def create_quete_quotidienne(quete: Quete, season_pass_id: str, user=Depends(get_current_user)):

    seasonPass_ref = firestore_db.collection("season_pass").document(season_pass_id)

    if not seasonPass_ref.get().exists:
        raise HTTPException(status_code=404, detail="Season pass not found")

    quete = quete.dict()
    quete_id = seasonPass_ref.collection("quetes_quotidienne").document().id
    seasonPass_ref.collection("quetes_quotidienne").document(quete_id).set(quete)
    quete["id"] = quete_id
    return quete


@app.post("/api/v1/season_pass/{season_pass_id}/quetes_hebdo/", response_model=QueteReturn)
def create_quete_quotidienne(quete: Quete, season_pass_id: str, user=Depends(get_current_user)):

    seasonPass_ref = firestore_db.collection("season_pass").document(season_pass_id)

    if not seasonPass_ref.get().exists:
        raise HTTPException(status_code=404, detail="Season pass not found")

    quete = quete.dict()
    quete_id = seasonPass_ref.collection("quetes_hebdo").document().id
    seasonPass_ref.collection("quetes_hebdo").document(quete_id).set(quete)
    quete["id"] = quete_id
    return quete


# Get user quetes
@app.get("/api/v1/user/quetes_quotidienne/", response_model=List[UserQuete])
def daily_quete_user(user_id: str = Depends(get_current_user)):

    # # get season pass actif
    # season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    # season_pass_list = []
    # for season_pass in season_pass:
    #     id = season_pass.id
    #     season_pass_dict = season_pass.to_dict()
    #     season_pass_dict["id"] = id
    #     season_pass_list.append(season_pass_dict)

    # if len(season_pass_list) == 0:
    #     raise HTTPException(status_code=404, detail="Season pass not found")

    # season_pass = season_pass_list[0]
    # # get the user season pass
    # user_season_pass = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).get()
    # if not user_season_pass.exists:
    #     # create user season pass
    #     user_season_pass = (
    #         firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).set({"xp": 0, "level": 0})
    #     )

    # # get user quetes daily
    # user_ref = (
    #     firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).collection("quetes_quotidienne")
    # )
    # date = datetime.now().strftime("%Y-%m-%d")
    # user_quetes = user_ref.where("date", "==", date).stream()
    # user_quetes = list(user_quetes)
    # if len(user_quetes) == 0:
    #     # create user quetes daily
    #     quetes = firestore_db.collection("season_pass").document(season_pass["id"]).collection("quetes_quotidienne").stream()
    #     quetes = list(quetes)
    #     res = []
    #     if len(quetes) == 0:
    #         raise HTTPException(status_code=404, detail="Quetes not found")
    #     for quete in quetes:
    #         queteres = {
    #             "quete_ref": quete.reference,
    #             "quota": 0,
    #             "date": date,
    #         }
    #         ref = user_ref.document()
    #         ref.set(queteres)
    #         queteres["id"] = ref.id
    #         queteres["queteId"] = quete.to_dict()
    #         queteres["queteId"]["id"] = quete.id
    #         res.append(queteres)
    #     return res
    # else:
    #     quetes = user_quetes
    #     res = []
    #     for user_quete in quetes:
    #         id = user_quete.id
    #         user_quete = user_quete.to_dict()
    #         quete_id = user_quete["quete_ref"].id
    #         quete_ref = user_quete["quete_ref"].get().to_dict()
    #         quete_ref["id"] = quete_id
    #         is_claimable = False
    #         if user_quete["quota"] >= quete_ref["quota"]:
    #             is_claimable = True
    #         dict = {
    #             "queteId": quete_ref,
    #             "id": id,
    #             "quota": user_quete["quota"],
    #             "date": user_quete["date"],
    #             "is_claimed": user_quete["is_claimed"] if "is_claimed" in user_quete else False,
    #             "is_claimable": is_claimable,
    #         }
    #         res.append(dict)
    return []


@app.get("/api/v1/user/quetes_hebdo/", response_model=List[UserQuete])
def hebdo_quete_user(user_id: str = Depends(get_current_user)):

    # # get season pass actif
    # season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    # season_pass_list = []
    # for season_pass in season_pass:
    #     id = season_pass.id
    #     season_pass_dict = season_pass.to_dict()
    #     season_pass_dict["id"] = id
    #     season_pass_list.append(season_pass_dict)

    # if len(season_pass_list) == 0:
    #     raise HTTPException(status_code=404, detail="Season pass not found")

    # season_pass = season_pass_list[0]
    # # get the user season pass
    # user_season_pass = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).get()
    # if not user_season_pass.exists:
    #     # create user season pass
    #     user_season_pass = (
    #         firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).set({"xp": 0, "level": 0})
    #     )

    # # get user quetes daily
    # user_ref = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).collection("quetes_hebdo")
    # date = datetime.now().strftime("%Y-%m-%d")
    # # check the quetes of monday
    # # get the date of the monday
    # date = datetime.now()
    # date = date - timedelta(days=date.weekday())
    # date = date.strftime("%Y-%m-%d")

    # # find the quetes of the week
    # user_quetes = user_ref.where("date", "==", date).stream()
    # user_quetes = list(user_quetes)
    # if len(user_quetes) == 0:
    #     # create user quetes daily
    #     quetes = firestore_db.collection("season_pass").document(season_pass["id"]).collection("quetes_hebdo").stream()
    #     quetes = list(quetes)
    #     res = []
    #     if len(quetes) == 0:
    #         raise HTTPException(status_code=404, detail="Quetes not found")
    #     for quete in quetes:
    #         queteres = {
    #             "quete_ref": quete.reference,
    #             "quota": 0,
    #             "date": date,
    #         }
    #         ref = user_ref.document()
    #         ref.set(queteres)
    #         queteres["id"] = ref.id
    #         queteres["queteId"] = quete.to_dict()
    #         queteres["queteId"]["id"] = quete.id
    #         res.append(queteres)
    #     return res
    # else:
    #     quetes = user_quetes
    #     res = []
    #     for user_quete in quetes:
    #         id = user_quete.id
    #         user_quete = user_quete.to_dict()
    #         quete_id = user_quete["quete_ref"].id
    #         quete_ref = user_quete["quete_ref"].get().to_dict()
    #         quete_ref["id"] = quete_id
    #         dict = {"queteId": quete_ref, "id": id, "quota": user_quete["quota"], "date": user_quete["date"]}
    #         res.append(dict)
    return []


# Claim quete
@app.post("/api/v1/user/quetes_quotidienne/{quete_id}/claim/")
def claim_quete_quo(quete_id: str, user_id: str = Depends(get_current_user)):
    # get season pass actif
    season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict["id"] = id
        season_pass_list.append(season_pass_dict)

    if len(season_pass_list) == 0:
        raise HTTPException(status_code=404, detail="Season pass not found")

    season_pass = season_pass_list[0]
    print(season_pass["id"])
    print(user_id)
    # get the user season pass
    user_season_pass_ref = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"])
    if not user_season_pass_ref.get().exists:
        # the user has not the season pass
        raise HTTPException(status_code=404, detail="User has not the season pass")

    # get the user quete
    user_ref = (
        firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).collection("quetes_quotidienne")
    )
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=404, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete["quete_ref"].get().to_dict()

    if "is_claimed" in user_quete and user_quete["is_claimed"]:
        raise HTTPException(status_code=404, detail="Quete already claimed")

    if user_quete["quota"] < season_pass_quete["quota"]:
        raise HTTPException(status_code=404, detail="Quete not completed")

    # claim the quete

    user_ref.document(quete_id).update({"is_claimed": True})

    # add xp to the user
    user_season_pass_ref.update({"xp": firestore.Increment(season_pass_quete["xp"])})


@app.post("/api/v1/user/quetes_hebdo/{quete_id}/claim/")
def claim_quete_hebdo(quete_id: str, user_id: str = Depends(get_current_user)):
    # get season pass actif
    season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict["id"] = id
        season_pass_list.append(season_pass_dict)

    if len(season_pass_list) == 0:
        raise HTTPException(status_code=404, detail="Season pass not found")

    season_pass = season_pass_list[0]
    print(season_pass["id"])
    print(user_id)
    # get the user season pass
    user_season_pass_ref = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"])
    if not user_season_pass_ref.get().exists:
        # the user has not the season pass
        raise HTTPException(status_code=404, detail="User has not the season pass")

    # get the user quete
    user_ref = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).collection("quetes_hebdo")
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=404, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete["quete_ref"].get().to_dict()

    if "is_claimed" in user_quete and user_quete["is_claimed"]:
        raise HTTPException(status_code=404, detail="Quete already claimed")

    if user_quete["quota"] < season_pass_quete["quota"]:
        raise HTTPException(status_code=404, detail="Quete not completed")

    # claim the quete

    user_ref.document(quete_id).update({"is_claimed": True})

    # add xp to the user
    user_season_pass_ref.update({"xp": firestore.Increment(season_pass_quete["xp"])})


@app.patch("/api/v1/user/quetes_quotidienne/{quete_id}/increment/")
def increment_quete_quo(quete_id: str, user_id: str = Depends(get_current_user)):
    # get season pass actif
    season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    season_pass_list = []
    for season_pass in season_pass:
        id = season_pass.id
        season_pass_dict = season_pass.to_dict()
        season_pass_dict["id"] = id
        season_pass_list.append(season_pass_dict)

    if len(season_pass_list) == 0:
        raise HTTPException(status_code=404, detail="Season pass not found")

    season_pass = season_pass_list[0]
    # get the user season pass
    user_season_pass_ref = firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"])
    if not user_season_pass_ref.get().exists:
        # the user has not the season pass
        raise HTTPException(status_code=404, detail="User has not the season pass")

    # get the user quete
    user_ref = (
        firestore_db.collection("users").document(user_id).collection("season_pass").document(season_pass["id"]).collection("quetes_quotidienne")
    )
    user_quete = user_ref.document(quete_id).get()
    if not user_quete.exists:
        raise HTTPException(status_code=404, detail="Quete not found")
    user_quete = user_quete.to_dict()
    season_pass_quete = user_quete["quete_ref"].get().to_dict()

    if "is_claimed" in user_quete and user_quete["is_claimed"]:
        raise HTTPException(status_code=404, detail="Quete already claimed")

    if user_quete["quota"] >= season_pass_quete["quota"]:
        raise HTTPException(status_code=404, detail="Quete already completed")

    # increment the quete

    user_ref.document(quete_id).update({"quota": firestore.Increment(1)})
