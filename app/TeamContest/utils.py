import numpy as np

from fastapi import HTTPException


async def count_blocs(score: list[dict], blocs: list) -> tuple[np.ndarray, dict]:
    """Returns the count of success for each blocs and zones"""
    
    num_blocs = len(blocs)

    # init counts
    max_zones = max(np.unique([bloc["zones"] for bloc in blocs]))
    zones_int = list(range(1, max_zones + 1))

    all_blocs = np.zeros(num_blocs, dtype=int)
    all_zones = {zone: np.zeros(num_blocs, dtype=int) for zone in zones_int}

    for team in score:
        team_blocs_mask = np.zeros(num_blocs, dtype=bool)
        team_zones = {zone: np.zeros(num_blocs, dtype=bool) for zone in zones_int}

        # fuse all the blocs of the team into one mask (1 if the bloc is scored, 0 otherwise)
        # and do the same for the zones

        for member_id in team["members"]:
            member = team["members"][member_id]
            scored_blocs: list[int] = member.get("blocs", [])
            if len(scored_blocs) != num_blocs:
                continue

            scored_blocs = np.array(scored_blocs, dtype=int)

            # = 1 if the bloc is scored
            # = 0 if the bloc is not scored
            # < 0 if zone is scored
            # e.g -1 if zone 1 is scored, -2 if both zone 1 and zone 2 is scored

            # don't add the blocs that are already scored
            team_blocs_mask = team_blocs_mask | (scored_blocs >= 1)
            team_zones = {zone: team_zones[zone] | (scored_blocs >= -zone) & (scored_blocs < 0) for zone in zones_int}

        # add the team mask to the global mask
        all_blocs += team_blocs_mask.astype(int)
        for zone in zones_int:
            all_zones[zone] += team_zones[zone].astype(int)

    return (
        all_blocs,
        all_zones
    )


async def dispatch_contest_scoring(contest_ref, filter_by: str = None):
    contest = await contest_ref.get(["scoringType"])
    contest_dict = contest.to_dict()
    scoringType = contest_dict.get("scoringType", "PPB")

    if scoringType == "PPB":
        return await calculate_PPB(contest_ref, filter_by)
    elif scoringType == "PPBZ":
        return await calculate_PPBZ(contest_ref, filter_by)
    elif scoringType == "FIXED":
        return await calculate_fixed(contest_ref, filter_by)
    else:
        raise HTTPException(status_code=400, detail="scoringType not found")


async def calculate_PPB(contest_ref, filter_by: str = None) -> list:
    """Point Per Bloc"""
    
    contest = await contest_ref.get(["blocs", "score", "roles"])
    contest_dict = contest.to_dict()

    roles = contest_dict.get("roles", [])
    blocs = contest_dict.get("blocs", [])
    score = contest_dict.get("score", {})
    filtered_score = filter_teams(score, filter_by)

    if not filtered_score or not blocs:
        return {}

    blocs_count, _ = await count_blocs(filtered_score, blocs)

    # (1000 / number of teams that scored the bloc) * role mult

    for team in filtered_score:
        team_roles = team.get("roles", {})
        team_score = 0
        for role_name in team_roles:
            member_id = team_roles[role_name]
            if not member_id:
                continue

            member = team["members"][f"u_{member_id}"]
            scored_blocs: list[int] = member.get("blocs", [])
            if len(scored_blocs) != len(blocs):
                continue
            
            member_points = 0
            for it, score_bloc in enumerate(scored_blocs):
                if score_bloc <= 0:
                    continue
                
                bloc = blocs[it]
                mult = bloc.get("multiplicator", [1] * len(roles))
                if len(mult) != len(roles):
                    mult = [1] * len(roles)

                role_mult = mult[roles.index(role_name)]
                bloc_points = 1000 / blocs_count[it]
                member_points += bloc_points * role_mult

            member["points"] = member_points

            team_score += member_points
        team["points"] = team_score

    return filtered_score 


async def calculate_PPBZ(contest_ref, filter_by: str = None):
    contest = await contest_ref.get(["blocs", "score", "roles", "pointsPerZone"])
    contest_dict = contest.to_dict()

    roles = contest_dict.get("roles", [])
    blocs = contest_dict.get("blocs", [])
    score = contest_dict.get("score", {})
    ppz = contest_dict.get("pointsPerZone", 500)
    filtered_score = filter_teams(score, filter_by)

    if not filtered_score or not blocs:
        return {}

    blocs_count, zones_count = await count_blocs(filtered_score, blocs)

    # (1000 / number of teams that scored the bloc) * role mult
    # ((500 / number of zones in the bloc) / number of teams that scored the zone) * role mult

    for team in filtered_score:
        team_roles = team.get("roles", {})

        team_score = 0
        for role_name in team_roles:
            member_id = team_roles[role_name]
            if not member_id:
                continue

            member = team["members"][f"u_{member_id}"]
            scored_blocs: list[int] = member.get("blocs", [])
            if len(scored_blocs) != len(blocs):
                continue
            
            member_points = 0
            for it, score_bloc in enumerate(scored_blocs):
                bloc = blocs[it]
                mult = bloc.get("multiplicator", [1] * len(roles))
                if len(mult) != len(roles):
                    mult = [1] * len(roles)

                role_mult = mult[roles.index(role_name)]

                if score_bloc == 1:
                    # add bloc points
                    bloc_points = 1000 / blocs_count[it]
                    member_points += bloc_points * role_mult

                elif score_bloc < 0:
                    # add zone points
                    zones: int = bloc["zones"]

                    # only count the most valuable zone
                    for zone in range(zones, 0, -1):
                        z = zones_count[zone][it]
                        if not z:
                            print("something wrong in the zones count")
                            continue

                        zone_points = (ppz / zones) / zones_count[zone][it]
                        member_points += zone_points * role_mult
                        break

            member["points"] = member_points
            team_score += member_points

        team["points"] = team_score
    return filtered_score 

async def calculate_fixed(contest_ref, filter_by: str = None):
    contest = await contest_ref.get(["blocs", "score", "roles", "pointsPerZone"])
    contest_dict = contest.to_dict()

    roles = contest_dict.get("roles", [])
    blocs = contest_dict.get("blocs", [])
    score = contest_dict.get("score", {})
    ppz = contest_dict.get("pointsPerZone", 500)
    filtered_score = filter_teams(score, filter_by)

    for team in filtered_score:
        team_roles = team.get("roles", {})

        team_score = 0
        for role_name in team_roles:
            member_id = team_roles[role_name]
            if not member_id:
                continue

            member = team["members"][f"u_{member_id}"]
            scored_blocs: list[int] = member.get("blocs", [])
            if len(scored_blocs) != len(blocs):
                continue
            
            member_points = 0
            for it, score_bloc in enumerate(scored_blocs):
                if score_bloc == 0:
                    continue

                bloc = blocs[it]
                bloc_points = bloc.get("points", 0)
                mult = bloc.get("multiplicator", [1] * len(roles))

                if len(mult) != len(roles):
                    mult = [1] * len(roles)

                role_mult = mult[roles.index(role_name)]

                if score_bloc > 0:
                    member_points += bloc_points * role_mult
                elif score_bloc < 0:
                    nb_zone = -score_bloc
                    member_points += ppz * nb_zone * role_mult

            member["points"] = member_points
            team_score += member_points
    
        team["points"] = team_score
    return filtered_score


def filter_teams(score: dict | list, filter_by: str) -> list:
    filtered = []

    if isinstance(score, dict):
        score = score.values()

    for team in score:
        members = team.get("members", {})
        if len(members) == 0:
            continue

        genders = [member.get("gender") for member in members.values()]
        jeunes = [member.get("age", 18) < 18 for member in members.values()]

        is_homme = all(g == "M" for g in genders)
        is_femme = all(g == "F" for g in genders)
        is_mixte = len(set(genders)) > 1
        is_jeune = all(jeunes)

        if filter_by == "Homme" and is_homme:
            filtered.append(team)
        elif filter_by == "Femme" and is_femme:
            filtered.append(team)
        elif filter_by == "Mixte" and is_mixte:
            filtered.append(team)
        elif filter_by == "Jeune" and is_jeune:
            filtered.append(team)

        if not filter_by or (filter_by not in ["Homme", "Femme", "Mixte", "Jeune"]):
            filtered.append(team)

    return filtered
