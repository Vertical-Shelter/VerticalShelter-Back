from ..settings import firestore_db, storage_client, BUCKET_NAME, app
from google.cloud import firestore


def updateSeasonPass(user, xp: int):
    # get actif season pass
    season_pass = firestore_db.collection("season_pass").where("is_active", "==", True).stream()
    season_pass = list(season_pass)
    if len(season_pass) == 0:
        return False

    season_pass_ref = season_pass[0].reference

    # update level of user season pass
    user_season_pass = user.collection("user_season_pass").where("season_pass_id", "==", season_pass_ref).stream()
    user_season_pass = list(user_season_pass)

    # if user has a season pass, then update it else create a new one
    if len(user_season_pass) == 0:
        user.collection("user_season_pass").add(
            {
                "season_pass_id": season_pass_ref,
                "xp": xp,
                "is_premium": False,
            }
        )
    else:
        # increment xp
        user_season_pass[0].reference.update(
            {
                "xp": firestore.Increment(xp),
            }
        )
    return True


def updateSeasonPassSentWall(user):
    return updateSeasonPass(user, 5)


def updateLessSeasonPassSentWall(user):
    return updateSeasonPass(user, -5)


def updateSeasonPassBeta(user):
    return updateSeasonPass(user, 45)


def updateLessSeasonPassBeta(user):
    return updateSeasonPass(user, -45)


def updateSeasonPasslike(user):
    # get actif season pass
    return updateSeasonPass(user, 5)


def updateLesseasonPasslike(user):
    return updateSeasonPass(user, -5)


def updateSeasonPassComment(user):
    return updateSeasonPass(user, 5)


def updateSeasonPassShare(user):
    return updateSeasonPass(user, 100)


def updateSeasonPassPostStoryInstagram(user):
    return updateSeasonPass(user, 500)


def updateSeasonPassTagComent(user):
    return updateSeasonPass(user, 10)


def updateSeasonPassFollowOnInstagram(user):
    return updateSeasonPass(user, 100)


def updateSeasonPassAffiliate(user):
    return updateSeasonPass(user, 100)
