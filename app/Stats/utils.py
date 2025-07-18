import datetime

from google.cloud import firestore

from ..settings import bq_client, TABLE_PATH


async def convert_old_sentwall_to_row(doc: firestore.DocumentSnapshot | firestore.AsyncDocumentReference):
    """Preprocess Firestore data for BigQuery."""

    if isinstance(doc, firestore.AsyncDocumentReference):
        doc = await doc.get()

    data = doc.to_dict()
    res = {}

    date = data.get("date", None)
    if not date:
        print("No date found")
        return None

    if isinstance(date, datetime.datetime):
        date = date.isoformat()

    res["date"] = date

    sentwall_id = doc.id
    user_id = doc.reference.parent.parent.id
    res["id"] = sentwall_id
    res["user_id"] = user_id

    wall_ref = data.get("wall", None)
    if not wall_ref:
        return None

    wall = await wall_ref.get()
    wall_dict = wall.to_dict()
    if not wall_dict:
        return None

    res["wall_id"] = wall_ref.id
    res["attributes"] = wall_dict.get("attributes", [])

    grade_ref = wall_dict.get("grade", None)
    grade_id = wall_dict.get("grade_id", None)
    if not grade_ref and not grade_id:
        return None

    if not grade_ref:
        grade_ref = wall_ref.parent.parent.parent.parent.collection("grades").document(grade_id)

    grade = await grade_ref.get()
    grade_dict = grade.to_dict()
    if not grade_dict:
        return None

    res["grade_id"] = grade_ref.id
    res["vgrade"] = grade_dict.get("vgrade", None)

    secteur_ref = wall_ref.parent.parent
    res["cloc_id"] = secteur_ref.parent.parent.id
    res["secteur_id"] = secteur_ref.id

    secteur = await secteur_ref.get()
    secteur_dict = secteur.to_dict()
    if not secteur_dict:
        return None

    secteur_label = secteur_dict.get("newlabel", None) or secteur_dict.get("label", None)
    if not secteur_label:
        return None

    res["secteur_label"] = secteur_label
    return res


async def upload_sentwall_stats(sentwall_ref: firestore.DocumentReference):
    """Upload sentwall data to BigQuery."""

    row = await convert_old_sentwall_to_row(sentwall_ref)
    if not row:
        print(f"Failed to convert sentwall {sentwall_ref.path} to bigquery row")
        return

    # Insert row into BigQuery
    err = bq_client.insert_rows_json(TABLE_PATH, [row])

    if err:
        print(f"Failed to insert row into BigQuery: {err, row}")