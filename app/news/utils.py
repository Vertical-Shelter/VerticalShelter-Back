import asyncio
import datetime
from typing import Dict, Optional
import logging

from firebase_admin import messaging

from ..settings import firestore_async_db, ENV_MODE


async def get_user_data(user_id: str) -> Optional[Dict]:
    doc = await firestore_async_db.collection("users").document(user_id).get()
    doc_dict = doc.to_dict() if doc.exists else None
    if doc_dict:
        doc_dict["id"] = doc.id
    return doc_dict


async def send_notification_user(title: str, body: str, fcm_token: str, image_url: str = None, data: Dict = None):
    if not fcm_token:
        return
    
    try:
        # convert args to string
        if data:
            data = {k: str(v) for k, v in data.items()}

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body, image=image_url),
            token=fcm_token,
            data=data,
        )
        messaging.send(message)
    except Exception as e:
        logging.error(f"Error sending notification to {fcm_token} title:{title} body:{body}; {e}")

async def send_notification_topic(title: str, body: str, topic: str, image_url: str = None, data: Dict = None):
    if not topic:
        return
    
    try:
        # convert args to string
        if data:
            data = {k: str(v) for k, v in data.items()}

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body, image=image_url),
            topic=topic,
            data=data,
        )
        messaging.send(message)
    except Exception as e:
        logging.error(f"Error sending notification to topic {topic} title:{title} body:{body}; {e}")

async def resend_notification_topic(notif, lang: str=None):
    notif_dict = await process_notif(notif, lang)
    send_notification_topic(notif_dict["title"], notif_dict["description"], notif_dict["topic"], notif_dict.get("image_url"))
    return notif_dict

async def create_news_entry(path: str, data: dict):
    _, ref = await firestore_async_db.collection(path).add(data)
    data["id"] = ref.id
    return data


# format: {lang: {notif_type: (title, body)}} body is a format string with one or more argument
LANGUAGES = {
    "en": {
        "NEW_FRIEND": ("New Friend Request", "{0} sent you a friend request"),
        "FRIEND_ACCEPTED": ("Friend Request Accepted", "{0} accepted your friend request"),
        "NEW_SECT": ("{0}New Sector", "{0} just created a new sector, check it out!"),
        "SOON_SECT": ("{0}Sector closing Soon", "\"{0}\" is closing soon, hurry up before it's too late!"),
        "NEWS": ("{0}", "{0}"),
        "NEW_CONTEST": ("{0}", "{0}"),
        "COMMENT": ("{0} commented on a wall", "{0}"),
        "VIDEO": ("{0} posted a video", "{0}"),
        "PAYMENT": ("Payment", "You have successfully paid for {0}"),
    },
    "fr": {
        "NEW_FRIEND": ("Nouvelle demande d'ami", "{0} vous a envoyé une demande d'ami"),
        "FRIEND_ACCEPTED": ("Demande d'ami acceptée", "{0} a accepté votre demande d'ami"),
        "NEW_SECT": ("{0}Nouveau Secteur", "{0} vous a concocté de nouvelles pépites, découvrez-les !"),
        "SOON_SECT": ("{0}Secteur fermant bientôt", "\"{0}\" ferme bientôt, dépêchez-vous avant qu'il ne soit trop tard !"),
        "NEWS": ("{0}", "{0}"),
        "NEW_CONTEST": ("{0}", "{0}"),
        "COMMENT": ("{0} a commenté un mur", "{0}"),
        "VIDEO": ("{0} a posté une vidéo", "{0}"),
        "PAYMENT": ("Paiement", "Vous avez payé avec succès pour les {0}"),
    },
    "es": {
        "NEW_FRIEND": ("Nueva solicitud de amistad", "{0} te ha enviado una solicitud de amistad"),
        "FRIEND_ACCEPTED": ("Solicitud de amistad aceptada", "{0} ha aceptado tu solicitud de amistad"),
        "NEW_SECT": ("{0}Nuevo Sector", "{0} acaba de crear un nuevo sector, ¡échale un vistazo!"),
        "SOON_SECT": ("{0}Sector cerrando pronto", "\"{0}\" está a punto de cerrar, ¡date prisa antes de que sea demasiado tarde!"),
        "NEWS": ("{0}", "{0}"),
        "NEW_CONTEST": ("{0}", "{0}"),
        "COMMENT": ("{0} ha comentado en un muro", "{0}"),
        "VIDEO": ("{0} ha publicado un video", "{0}"),
        "PAYMENT": ("Pago", "Has pagado con éxito por {0}"),
    },
    "de": {
        "NEW_FRIEND": ("Neue Freundschaftsanfrage", "{0} hat dir eine Freundschaftsanfrage gesendet"),
        "FRIEND_ACCEPTED": ("Freundschaftsanfrage angenommen", "{0} hat deine Freundschaftsanfrage angenommen"),
        "NEW_SECT": ("{0}Neuer Sektor", "{0} hat gerade einen neuen Sektor eingerichtet, schau ihn dir an!"),
        "SOON_SECT": ("{0}Sektor schließt bald", "\"{0}\" schließt bald, beeil dich, bevor es zu spät ist!"),
        "NEWS": ("{0}", "{0}"),
        "NEW_CONTEST": ("{0}", "{0}"),
        "COMMENT": ("{0} hat einen Kommentar auf einer Wand hinterlassen", "{0}"),
        "VIDEO": ("{0} hat ein Video gepostet", "{0}"),
        "PAYMENT": ("Zahlung", "Sie haben erfolgreich für {0} bezahlt"),
    },
}

SUBTOPICS = list(LANGUAGES["fr"].keys())


def construct_notif(lang: str, notif_type: str, title_params: list, body_params: list):
    title, body_format = LANGUAGES[lang].get(notif_type, ("", ""))
    title = title.format(*title_params)
    body = body_format.format(*body_params)
    return title, body


def try_fmt(fmt: str, *args):
    # this is a fallback in case the payload is not formatted correctly,
    # most likely due to a change in the format of the news
    # -> would most likely be for old news / notifs

    # replace formats with empty string
    try:
        return fmt.format(*args)
    except IndexError:
        return fmt.format(*[""] * len(fmt))


def process_notif(notif, lang: str=None):
    notif_dict = notif.to_dict()
    if not lang or lang not in LANGUAGES:
        lang = "fr"

    if notif_dict.get("title") and notif_dict.get("description"):
        return notif_dict

    title_format, body_format = LANGUAGES[lang].get(notif_dict["news_type"], ("", ""))
    title = try_fmt(title_format, *notif_dict["title_payload"])
    body = try_fmt(body_format, *notif_dict["body_payload"])

    notif_dict["title"] = title
    notif_dict["description"] = body
    notif_dict["id"] = notif.id

    return notif_dict


async def handle_notif(notif_type: str, title_params: list, body_params: list, notif_topic: str = None, dest_user: Dict = None, image_url: str = None, do_send_image=True, **data):
    if ENV_MODE != "prod":
        return # don't send notifs in CI (je tiens à mon travail)

    if dest_user and not isinstance(dest_user, dict):
        # create the user dict stuff and get the id
        tmp = dest_user.to_dict()
        dest_user = {"id": dest_user.reference.id, **tmp}
    
    if notif_type not in LANGUAGES["fr"]:
        logging.warning(f"Unknown notif type {notif_type}")
        return

    # send notification to topic
    if notif_topic:
        # try to get the notif_topic doc, create it if it doesn't exist
        notif_topic_doc = await firestore_async_db.collection("News").document(notif_topic).get()
        if not notif_topic_doc.exists:
            await firestore_async_db.collection("News").document(notif_topic).set({})

        # if there is a news of the same type in the last 12 hours,
        # update it and don't send a new notification
        if notif_type == "NEW_SECT":
            last_news_stream = (
                firestore_async_db.collection(f"News/{notif_topic}/news")
                .order_by("date", direction="DESCENDING")
                .where("news_type", "==", notif_type)
                .limit(1)
                .stream()
            )

            async for last_news in last_news_stream:
                last_news_ref = last_news.reference
                last_news_dict = last_news.to_dict()
                last_news_date = last_news_dict["date"]
                # less than 12 hours, update the last news date
                if (datetime.datetime.now(datetime.timezone.utc) - last_news_date).seconds < 60 * 60 * 12:
                    date = datetime.datetime.now()
                    last_news_dict["date"] = date
                    await last_news_ref.update({"date": datetime.datetime.now()})
                    return last_news_dict

        # create the news entry
        path = f"News/{notif_topic}/news"
        news_dict = await create_news_entry(
            path,
            {
                "news_type": notif_type,
                "topic": notif_topic,
                "title_payload": title_params,
                "body_payload": body_params,
                "image_url": image_url,
                "args": data,
                "date": datetime.datetime.now(),
            }
        )

        data.update({"news_type": notif_type})
        if not do_send_image:
            image_url = None

        tasks = []
        for lang in LANGUAGES:
            title, body = construct_notif(lang, notif_type, title_params, body_params)
            if not title or not body:
                continue

            topic = f"{notif_topic}_{lang}"
            tasks.append(send_notification_topic(title, body, topic, image_url=image_url, data=data))

        # send fr notif to the default topic
        title, body = construct_notif("fr", notif_type, title_params, body_params)
        tasks.append(send_notification_topic(title, body, notif_topic, image_url=image_url, data=data))

        await asyncio.gather(*tasks)
        return news_dict

    # send notification to user
    elif dest_user and dest_user.get("id") and dest_user.get("fcm_token"):
        path = f"users/{dest_user["id"]}/news"
        news_dict = await create_news_entry(
            path,
            {
                "news_type": notif_type,
                "topic": dest_user["id"],
                "title_payload": title_params,
                "body_payload": body_params,
                "image_url": image_url,
                "args": data,
                "date": datetime.datetime.now(),
            }
        )

        data.update({"news_type": notif_type})
        if not do_send_image:
            image_url = None

        lang = dest_user.get("lang", "fr")
        token = dest_user.get("fcm_token")

        title, body = construct_notif(lang, notif_type, title_params, body_params)
        await send_notification_user(title, body, token, image_url=image_url, data=data)
        return news_dict

    logging.warning(f"No destination for notification {notif_type}, {title_params}, {body_params} perhaps missing a topic or user fcm_token")
    return


async def send_invite_to_user(inviter_id: str, invitee_id: str):
    inviter_data = await get_user_data(inviter_id)
    invitee_data = await get_user_data(invitee_id)

    if not inviter_data or not invitee_data:
        return False

    await handle_notif(
        "NEW_FRIEND",
        [],
        [inviter_data["username"]],
        dest_user=invitee_data,
        friend_id=inviter_id,
    )

    return True

async def send_friend_accepted_to_user(accepter_id: str, requester_id: str):
    accepter_data = await get_user_data(accepter_id)
    requester_data = await get_user_data(requester_id)

    if not accepter_data or not requester_data:
        return False

    await handle_notif(
        "FRIEND_ACCEPTED",
        [],
        [accepter_data["username"]],
        dest_user=requester_data,
        friend_id=accepter_id,
    )

    return True
