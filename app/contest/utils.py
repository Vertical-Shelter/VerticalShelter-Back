import asyncio
import logging
import time

from fastapi import HTTPException
from firebase_admin import firestore

from ..settings import firestore_async_db, firestore_db
from .models import ListIsBlocSucceed


async def get_contest_blocs(contest_ref) -> list:
    blocs_collection = contest_ref.collection("blocs")
    blocs = await blocs_collection.get()

    blocs_list = []
    for bloc in blocs:
        bloc_dict = bloc.to_dict()
        bloc_dict["id"] = bloc.id
        blocs_list.append(bloc_dict)

    # put the blocs in the right order to avoid any issues with encoding / decoding
    blocs_list.sort(key=lambda x: x["numero"])
    return blocs_list 

async def get_inscriptions(contest_ref) -> list:
    inscriptions_collection = contest_ref.collection("inscription")
    inscriptions = await inscriptions_collection.get()

    inscriptions_list = []
    for inscription in inscriptions:
        inscription_dict = inscription.to_dict()
        inscription_dict["id"] = inscription.id
        inscription_dict["phaseId"] = None
        inscriptions_list.append(inscription_dict)

    return inscriptions_list
    
async def count_blocs(contest_blocs: list, inscriptions: dict):
    """Returns the count of success for each blocs for each categories (M, F, global)"""

    blocs_count = {"M": {}, "F": {}, "global": {}}
    for bloc in contest_blocs:
        bloc_id = bloc["id"]
        blocs_count["M"][bloc_id] = 0
        blocs_count["F"][bloc_id] = 0
        blocs_count["global"][bloc_id] = 0

    for inscription in inscriptions:
        genre = inscription.get("genre", "M")

        blocs_enc = inscription.get("blocs_enc", [])
        if not blocs_enc:
            continue

        blocs_dec = decode_score(blocs_enc, contest_blocs)

        for bloc in contest_blocs:
            bloc_id = bloc["id"]

            if bloc_id not in blocs_dec:
                logging.warning(f"bloc {bloc_id} not found in inscription {inscription['id']}, something might be wrong")
                continue

            if blocs_dec[bloc_id]["isSucceed"] == True:
                blocs_count["global"][bloc_id] += 1
                blocs_count[genre][bloc_id] += 1

    return blocs_count

async def count_zones(contest_blocs: list, inscriptions: dict):
    """Returns the count of success for each zones for each categories (M, F, global)"""

    zones_count = {"M": {}, "F": {}, "global": {}}
    for bloc in contest_blocs:
        bloc_id = bloc["id"]
        zones_count["M"][bloc_id] = {}
        zones_count["F"][bloc_id] = {}
        zones_count["global"][bloc_id] = {}

        num_zones = bloc.get("zones", 0)
        for it in range(num_zones):
            zones_count["M"][bloc_id][it] = 0
            zones_count["F"][bloc_id][it] = 0
            zones_count["global"][bloc_id][it] = 0

    for inscription in inscriptions:
        genre = inscription.get("genre", "M")

        blocs_enc = inscription.get("blocs_enc", [])
        if not blocs_enc:
            continue

        blocs_dec = decode_score(blocs_enc, contest_blocs)

        for bloc in contest_blocs:
            bloc_id = bloc["id"]

            if bloc_id not in blocs_dec:
                logging.warning(f"bloc {bloc_id} not found in inscription {inscription['id']}, something might be wrong")
                continue

            for it, isZoneSucceed in enumerate(blocs_dec[bloc_id].get("isZoneSucceed", [])):
                if isZoneSucceed == True:
                    zones_count["global"][bloc_id][it] += 1
                    zones_count[genre][bloc_id][it] += 1

    return zones_count


async def dispatch_contest_scoring(contest_ref):
    contest = await contest_ref.get(["scoringType"])
    contest_dict = contest.to_dict()
    scoringType = contest_dict.get("scoringType", "PPB")

    if scoringType == "PPB":
        return await calculate_PPB(contest_ref)
    elif scoringType == "PPBZ":
        return await calculate_PPBZ(contest_ref)
    else:
        raise HTTPException(status_code=400, detail="scoringType not found")


async def calculate_PPB(contest_ref):
    inscriptions_task = get_inscriptions(contest_ref)
    contest_blocs_task = get_contest_blocs(contest_ref)
    contest_blocs, inscriptions = await asyncio.gather(contest_blocs_task, inscriptions_task)

    blocs_count = await count_blocs(contest_blocs, inscriptions)
    
    global_scores = []
    F_scores = []
    M_scores = []

    for inscription in inscriptions:
        genre = inscription.get("genre", "M")
        global_points = 0
        gender_points = 0
        nbZone = 0

        blocs_enc = inscription.get("blocs_enc", [])
        blocs_dec = decode_score(blocs_enc, contest_blocs)

        # sum the points for each bloc
        for bloc in contest_blocs:
            bloc_id = bloc["id"]

            if not blocs_enc:
                continue

            if bloc_id not in blocs_dec:
                logging.warning(f"bloc {bloc_id} not found in inscription {inscription['id']}, something might be wrong")
                continue

            if blocs_dec[bloc_id]["isSucceed"] == True:
                global_points += int(1000 / blocs_count["global"][bloc_id])
                gender_points += int(1000 / blocs_count[genre][bloc_id])

            nbZone += blocs_dec[bloc_id].get("isZoneSucceed", []).count(True)

        inscription["nbZone"] = nbZone
        inscription["blocs"] = list(blocs_dec.values())

        inscription_genre = inscription.copy()
        inscription_genre["points"] = gender_points
        inscription["points"] = global_points

        if genre == "M":
            M_scores.append(inscription_genre)
        elif genre == "F":
            F_scores.append(inscription_genre)
        global_scores.append(inscription)

    global_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)
    F_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)
    M_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)

    # remove "blocs" key from each inscription
    to_update = {"global": [], "F": [], "M": []}
    for inscription in global_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["global"].append(cp)
    for inscription in F_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["F"].append(cp)
    for inscription in M_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["M"].append(cp)

    await contest_ref.update(to_update)
    return {"global": global_scores, "M": M_scores, "F": F_scores}


async def calculate_PPBZ(contest_ref):
    inscriptions_task = get_inscriptions(contest_ref)
    contest_blocs_task = get_contest_blocs(contest_ref)
    contest_blocs, inscriptions, contest_min = await asyncio.gather(
        contest_blocs_task,
        inscriptions_task,
        contest_ref.get(["pointsPerZone"]),
    )

    contest_dict = contest_min.to_dict()
    ppz = contest_dict.get("pointsPerZone", 500)

    blocs_count = await count_blocs(contest_blocs, inscriptions)
    zones_count = await count_zones(contest_blocs, inscriptions)
    
    global_scores = []
    F_scores = []
    M_scores = []

    for inscription in inscriptions:
        genre = inscription.get("genre", "M")
        global_points = 0
        gender_points = 0
        nbZone = 0

        blocs_enc = inscription.get("blocs_enc", [])
        blocs_dec = decode_score(blocs_enc, contest_blocs)

        # sum the points for each bloc / zones
        for bloc in contest_blocs:
            bloc_id = bloc["id"]

            if not blocs_enc:
                continue

            if bloc_id not in blocs_dec:
                logging.warning(f"bloc {bloc_id} not found in inscription {inscription['id']}, something might be wrong")
                continue

            if blocs_dec[bloc_id]["isSucceed"] == True:
                global_points += int(1000 / blocs_count["global"][bloc_id])
                gender_points += int(1000 / blocs_count[genre][bloc_id])
            elif bloc.get("zones", 0):
                num_zones = bloc["zones"]
                points_per_zone = ppz / num_zones

                for it, isZoneSucceed in enumerate(blocs_dec[bloc_id].get("isZoneSucceed", [])):
                    if isZoneSucceed == True:
                        global_points += int(points_per_zone / zones_count["global"][bloc_id].get(it, 0))
                        gender_points += int(points_per_zone / zones_count[genre][bloc_id].get(it, 0))

            nbZone += blocs_dec[bloc_id].get("isZoneSucceed", []).count(True)

        inscription["nbZone"] = nbZone
        inscription["blocs"] = list(blocs_dec.values())

        inscription_genre = inscription.copy()
        inscription_genre["points"] = gender_points
        inscription["points"] = global_points

        if genre == "M":
            M_scores.append(inscription_genre)
        elif genre == "F":
            F_scores.append(inscription_genre)
        global_scores.append(inscription)

    global_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)
    F_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)
    M_scores.sort(key=lambda x: (x["points"], x["nbZone"]), reverse=True)

    # remove "blocs" key from each inscription
    to_update = {"global": [], "F": [], "M": []}
    for inscription in global_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["global"].append(cp)
    for inscription in F_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["F"].append(cp)
    for inscription in M_scores:
        cp = inscription.copy()
        cp.pop("blocs", None)
        to_update["M"].append(cp)

    await contest_ref.update(to_update)
    return {"global": global_scores, "M": M_scores, "F": F_scores}


async def get_contest(doc, climbingLocation_id, contest_id, uid):
    dict_doc = doc.to_dict()
    dict_doc["id"] = doc.id

    async def get_blocs():
        blocs = (
            firestore_async_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("contest")
            .document(contest_id)
            .collection("blocs")
            .stream()
        )

        def _get_bloc(bloc):
            bloc_dict = bloc.to_dict()
            bloc_dict["id"] = bloc.id
            return bloc_dict

        dict_doc["blocs"] = [_get_bloc(bloc) async for bloc in blocs]
        dict_doc["blocs"].sort(key=lambda x: x["numero"])

    async def get_phases():
        phases = (
            firestore_async_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("contest")
            .document(contest_id)
            .collection("phase")
            .stream()
        )

        def _get_phase(phase):
            phase_dict = phase.to_dict()
            phase_dict["id"] = phase.id
            return phase_dict

        dict_doc["phases"] = [_get_phase(phase) async for phase in phases]

    async def get_inscriptionList():
        inscriptions = (
            firestore_async_db.collection("climbingLocations")
            .document(climbingLocation_id)
            .collection("contest")
            .document(contest_id)
            .collection("inscription")
            .stream()
        )

        async def _get_inscription(inscription):
            inscription_dict = inscription.to_dict()

            phase_ref = await inscription_dict.get("phaseId").get()
            if phase_ref.exists:
                inscription_dict["phaseId"] = phase_ref.to_dict()
                inscription_dict["phaseId"]["id"] = phase_ref.id

            if inscription_dict.get("user_ref") and inscription_dict.get("user_ref").id == uid:
                blocs_enc = inscription_dict.get("blocs_enc", [])
                blocs_list = list(decode_score(blocs_enc, dict_doc["blocs"]).values())
            else:
                blocs_list = []

            res = {
                "id": inscription.id,
                "genre": inscription_dict.get("genre"),
                "nom": inscription_dict.get("nom"),
                "prenom": inscription_dict.get("prenom"),
                "isMember": inscription_dict.get("isMember"),
                "is18YO": inscription_dict.get("is18YO"),
                "isGuest": inscription_dict.get("isGuest"),
                "phaseId": inscription_dict.get("phaseId"),
                "blocs": blocs_list,
            }

            if inscription_dict.get("user_ref") is not None:
                user = await inscription_dict.get("user_ref").get()
                user_dict = user.to_dict()
                user_dict["id"] = user.id
                user_dict["all_banieres"] = []
                user_dict["all_avatars"] = []
                user_dict["baniere"] = None
                user_dict["avatar"] = None
                user_dict["climbingLocation_id"] = None
                res["user"] = user_dict

                if user.id == uid:
                    dict_doc["qrCodeScanned"] = True
                    dict_doc["isSubscribed"] = True

            else:
                res["user"] = {
                    "id": "Guest",
                    "username": "Guest : "
                    + inscription_dict["nom"]
                    + " "
                    + inscription_dict["prenom"],
                }

            return res

        dict_doc["isSubscribed"] = False
        dict_doc["qrCodeScanned"] = False
        dict_doc["inscriptionList"] = await asyncio.gather(
            *[_get_inscription(inscription) async for inscription in inscriptions]
        )

    await get_blocs()
    await asyncio.gather(get_phases(), get_inscriptionList())
    return dict_doc

def encode_score(score: ListIsBlocSucceed, contest_blocs):
    """
    when bloc is not succeed, it is encoded as -zones succeeded count (if no zones, 0)
    when bloc is succeed, it is encoded as 1
    """
    blocs_encoded: list[int] = []
    score_dict = {bloc.blocId: bloc for bloc in score.score}

    for bloc in contest_blocs:
        bloc_id = bloc["id"]
        bloc_encoded = 0

        if score_dict.get(bloc_id) is not None:
            nbZones = score_dict[bloc_id].isZoneSucceed.count(True)
            bloc_encoded = 1 if score_dict[bloc_id].isSucceed else -nbZones

        blocs_encoded.append(bloc_encoded)

    return blocs_encoded

def decode_score(blocs_encoded: list[int], contest_blocs) -> dict:
    """Decode the score from the encoded version, tkt trust le process"""

    score_dict = {}
    for bloc, bloc_encoded in zip(contest_blocs, blocs_encoded):
        bloc_id = bloc["id"]
        isSucceed = bloc_encoded == 1

        tot_zone = bloc.get("zones", 0)
        if isSucceed:
            isZoneSucceed = [True] * tot_zone
        else:
            isZoneSucceed = [False] * tot_zone

        if bloc_encoded < 0:
            for i in range(-bloc_encoded):
                isZoneSucceed[i] = True

        score_dict[bloc_id] = {"blocId": bloc_id, "isSucceed": isSucceed, "isZoneSucceed": isZoneSucceed}
    return score_dict

async def scoring_contest(contest_ref, inscription, score: ListIsBlocSucceed):
    contest_blocs = await get_contest_blocs(contest_ref)
    blocs_encoded = encode_score(score, contest_blocs)
    await inscription.reference.update({"blocs_enc": blocs_encoded})

    # smart refresh
    infos = (await contest_ref.get(["last_calculated", "num_without_update"])).to_dict()
    last_calculated = infos.get("last_calculated", 0)
    num_without_update = infos.get("num_without_update", 0)

    if num_without_update < 10 and (time.time() - last_calculated) < 60:
        await contest_ref.update({"num_without_update": firestore.Increment(1)})
    else:
        await contest_ref.update({"last_calculated": time.time(), "num_without_update": 0})
        await dispatch_contest_scoring(contest_ref)

    return {"message": "Score added successfully"}