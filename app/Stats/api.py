from datetime import datetime

from fastapi import Depends
from google.cloud.bigquery import Client
from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig

from ..settings import app, firestore_async_db, bq_client
from ..User.deps import get_current_user
from .models import ClocStatsResp, WallStatsResp


@app.get("/api/v1/stats/user/", response_model=list[ClocStatsResp], response_model_exclude_unset=True)
async def get_user_stats(
    climbingLocation_id: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    user_id: str = Depends(get_current_user),
):
    """
    Get stats for a user, filtered by attributes, cloc, and date range
    If no climbingLocation_id is provided, the stats will be for all climbing locations
    """

    query = f"""
    SELECT
        id,
        date,
        cloc_id,
        attributes,
        vgrade,
        grade_id,
    FROM
        `vertical-shelter-411517.statistics.sentwalls`
    WHERE
        user_id = @user_id
    """
    
    params = [ScalarQueryParameter("user_id", "STRING", user_id)]
    
    if climbingLocation_id:
        query += " AND cloc_id = @climbingLocation_id"
        params.append(ScalarQueryParameter("climbingLocation_id", "STRING", climbingLocation_id))
    
    if start_date:
        query += " AND date >= TIMESTAMP(@start_date)"
        params.append(ScalarQueryParameter("start_date", "STRING", start_date.isoformat()))
    
    if end_date:
        query += " AND date <= TIMESTAMP(@end_date)"
        params.append(ScalarQueryParameter("end_date", "STRING", end_date.isoformat()))

    query += " ORDER BY date DESC"

    job_config = QueryJobConfig(query_parameters=params)
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()
    sentwalls = [dict(row) for row in results]

    res = {}
    for sentwall in sentwalls:
        cloc_id = sentwall["cloc_id"]

        if cloc_id not in res:
            res[cloc_id] = {
                "id": cloc_id,
                "count_sentwalls": 0,
                "count_attributes": {},
                "count_grades": {},
                "sessions": {},
            }

        cloc_dict = res[cloc_id]
        cloc_dict["count_sentwalls"] += 1

        # count_grades
        grade_count, _ = cloc_dict["count_grades"].get(sentwall["grade_id"], (0, 0))
        cloc_dict["count_grades"][sentwall["grade_id"]] = (grade_count + 1, int(sentwall["vgrade"]))

        # count_attributes
        for attribute in sentwall["attributes"]:
            cloc_dict["count_attributes"][attribute] = cloc_dict["count_attributes"].get(attribute, 0) + 1

        # add sentwall to sessions
        date = sentwall["date"].strftime("%Y-%m-%d")
        if date not in cloc_dict["sessions"]:
            cloc_dict["sessions"][date] = []

        cloc_dict["sessions"][date].append(sentwall)

    for cloc_id, cloc_dict in res.items():
        # sorted count_grade by vgrade
        grade_count = sorted(cloc_dict["count_grades"].items(), key=lambda x: x[1][1], reverse=True)
        grade_count = {k: v[0] for k, v in grade_count}

        # sort attributes by count
        cloc_dict["count_attributes"] = dict(sorted(cloc_dict["count_attributes"].items(), key=lambda x: x[1], reverse=True))
        cloc_dict["count_grades"] = grade_count

    return list(res.values())


@app.get("/api/v1/stats/ouvreur/", response_model=list[WallStatsResp], response_model_exclude_unset=True)
async def get_ouvreur_stats(
    climbingLocation_id: str,
    start_date: datetime = None,
    end_date: datetime = None,
    user_id: str = Depends(get_current_user),
):
    """
    Get stats for an ouvreur, filtered by attributes, cloc, and date range
    If no climbingLocation_id is provided, the stats will be for all climbing locations
    """

    query = f"""
    SELECT
        COUNT(id) as count_sentwalls,
        wall_id,
        grade_id,
        secteur_label,
        secteur_id,
        MIN(DATE(date)) as date,
        ARRAY_AGG(
            STRUCT(DATE(date) as date)
        ) as sentwalls,
    FROM
        `vertical-shelter-411517.statistics.sentwalls`
    WHERE
        cloc_id = @climbingLocation_id
    """

    params = [ScalarQueryParameter("climbingLocation_id", "STRING", climbingLocation_id)]

    if start_date:
        query += " AND date >= TIMESTAMP(@start_date)"
        params.append(ScalarQueryParameter("start_date", "STRING", start_date.isoformat()))

    if end_date:
        query += " AND date <= TIMESTAMP(@end_date)"
        params.append(ScalarQueryParameter("end_date", "STRING", end_date.isoformat()))

    query += f"""
    GROUP BY
        secteur_label,
        secteur_id,
        grade_id,
        wall_id
    ORDER BY
        date DESC,
        secteur_label
    """

    job_config = QueryJobConfig(query_parameters=params)
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()
    res = [dict(row) for row in results]
    
    for row in res:
        # sessions: date: count sentwalls
        sentwalls = row.pop("sentwalls")
        row["sentwalls"] = {}
        for sentwall in sentwalls:
            date = sentwall["date"].strftime("%Y-%m-%d")
            row["sentwalls"][date] = row["sentwalls"].get(date, 0) + 1

        row["date"] = row["date"].strftime("%Y-%m-%d")

    return res
