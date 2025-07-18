from ..settings import firestore_db, firestore_async_db, storage_client, BUCKET_NAME, app
from .utils import *
from .deps import get_current_user
from enum import Enum
from google.cloud import firestore

# User api
from .friends import *
from .stats import *


class Skill(Enum):
    Maitre_des_blocs = "Maitre des blocs"
    Video_Star = "Vidéo Star"
    Analytique_Averti = "Analytique Averti"
    Conquérant_de_Salle = "Conquérant de Salle"
    Créateur_de_Communauté = "Créateur de Communauté"


skills_name_desc = [
    {
        "display_name": "Maitre des blocs",
        "intern_name": Skill.Maitre_des_blocs.name,
        "description": "Réussi un max de bloc et deviens maitre des blocs",
        "icon": "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/icons/maitre_des_blocs.svg",
    },
    {
        "display_name": "Vidéo Star",
        "intern_name": Skill.Video_Star.name,
        "description": "Partage tes vidéos et deviens une star",
        "icon": "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/icons/vid%C3%A9o_star.svg",
    },
    {
        "display_name": "Analytique Averti",
        "intern_name": Skill.Analytique_Averti.name,
        "description": "Donne ton avis sur les blocs et deviens un expert",
        "icon": "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/icons/Analytique_averti.svg",
    },
    {
        "display_name": "Conquérant de Salle",
        "intern_name": Skill.Conquérant_de_Salle.name,
        "description": "Conquiert un max de salle et deviens un conquérant",
        "icon": "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/icons/Conqu%C3%A9rant%20de%20salle.svg",
    },
    {
        "display_name": "Créateur de Communauté",
        "intern_name": Skill.Créateur_de_Communauté.name,
        "description": "Participe activement à la création de notre communauté",
        "icon": "https://storage.googleapis.com/vertical-shelter-411517_prod_statics/icons/Cr%C3%A9ateur%20de%20communaut%C3%A9.svg",
    },
]


@app.get("/api/v1/user/me/skills/")
async def get_skills(uid: dict = Depends(get_current_user)):
    user = firestore_db.collection("users").document(uid).collection("skills").stream()
    list_skills = list(user)
    if len(list_skills) == 0:
        for skill in skills_name_desc:
            firestore_db.collection("users").document(uid).collection("skills").add(
                {
                    "display_name": skill["display_name"],
                    "intern_name": skill["intern_name"],
                    "level": 1,
                    "description": skill["description"],
                    "icon": skill["icon"],
                    "xp_next_level": 100,
                    "xp_current_level": 0,
                }
            )
        user = firestore_db.collection("users").document(uid).collection("skills").stream()
        list_skills = [doc.to_dict() for doc in user]
        return list_skills
    res = []

    for skill in list_skills:
        skill_dict = skill.to_dict()
        skill_dict["xp_next_level"] = int(skill_dict["xp_next_level"])
        skill_dict["xp_current_level"] = int(skill_dict["xp_current_level"])
        res.append(skill_dict)
    return res


def updateSkillPlus(skillName: Skill, user, points):
    video_skill = user.collection("skills").where("intern_name", "==", skillName.name).get()
    if len(video_skill) > 0:
        video_skill_dict = video_skill[0].to_dict()
        if video_skill_dict["xp_current_level"] + points >= video_skill_dict["xp_next_level"]:
            video_skill[0].reference.update(
                {
                    "xp_current_level": 0,
                    "xp_next_level": firestore.Increment(video_skill_dict["xp_next_level"]),
                    "level": firestore.Increment(1),
                }
            )
        else:
            video_skill = video_skill[0].reference.update(
                {
                    "xp_current_level": firestore.Increment(points),
                }
            )

async def async_updateSkillPlus(skillName: Skill, user, points):
    video_skill = await user.collection("skills").where("intern_name", "==", skillName.name).get()
    if len(video_skill) > 0:
        video_skill_dict = video_skill[0].to_dict()
        if video_skill_dict["xp_current_level"] + points >= video_skill_dict["xp_next_level"]:
            await video_skill[0].reference.update(
                {
                    "xp_current_level": 0,
                    "xp_next_level": firestore.Increment(video_skill_dict["xp_next_level"]),
                    "level": firestore.Increment(1),
                }
            )
        else:
            await video_skill[0].reference.update(
                {
                    "xp_current_level": firestore.Increment(points),
                }
            )

def updateSkillLess(skillName: Skill, user, points):
    video_skill = user.collection("skills").where("intern_name", "==", skillName.name).get()
    if len(video_skill) > 0:
        video_skill_dict = video_skill[0].to_dict()
        if video_skill_dict["xp_current_level"] - points < 0 and video_skill_dict["level"] > 1:
            last_level_max_points = int(video_skill_dict["xp_next_level"] - video_skill_dict["xp_next_level"] / 2)
            video_skill[0].reference.update(
                {
                    "xp_current_level": last_level_max_points - points,
                    "xp_next_level": last_level_max_points,
                    "level": firestore.Increment(-1),
                }
            )
        elif video_skill_dict["xp_current_level"] - points >= 0:
            video_skill = video_skill[0].reference.update(
                {
                    "xp_current_level": firestore.Increment(-points),
                }
            )

async def async_updateSkillLess(skillName: Skill, user, points):
    video_skill = await user.collection("skills").where("intern_name", "==", skillName.name).get()
    if len(video_skill) > 0:
        video_skill_dict = video_skill[0].to_dict()
        if video_skill_dict["xp_current_level"] - points < 0 and video_skill_dict["level"] > 1:
            last_level_max_points = int(video_skill_dict["xp_next_level"] - video_skill_dict["xp_next_level"] / 2)
            await video_skill[0].reference.update(
                {
                    "xp_current_level": last_level_max_points - points,
                    "xp_next_level": last_level_max_points,
                    "level": firestore.Increment(-1),
                }
            )
        elif video_skill_dict["xp_current_level"] - points >= 0:
            await video_skill[0].reference.update(
                {
                    "xp_current_level": firestore.Increment(-points),
                }
            )