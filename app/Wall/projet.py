import asyncio
import datetime
from typing import List, Optional

import regex as re
from fastapi import (BackgroundTasks, Body, Depends, File, Form, HTTPException,
                     UploadFile, status)

from ..settings import (BUCKET_NAME, app, firestore_async_db, firestore_db,
                        storage_client)
from ..User.deps import get_current_user
from .models import Project, ProjectResp
from .utils import get_project_data


@app.post("/api/v1/user/me/project/", response_model=ProjectResp)
async def create_project(
    projet: Project = Body(...),
    current_user: str = Depends(get_current_user),
):
    """
    Create a new project
    """

    #check if the user exist
    user = firestore_db.collection("users").document(current_user).get()
    if not user.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # get all the references 
    cloc_Ref = firestore_async_db.collection("climbingLocations").document(projet.climbingLocation_id)

    # different reference path for spraywall and wall
    if not projet.is_spraywall:
        secteur_Ref = cloc_Ref.collection("secteurs").document(projet.secteur_id)
        wall_ref = secteur_Ref.collection("walls").document(projet.wall_id)
    else:
        secteur_Ref = cloc_Ref.collection("spraywalls").document(projet.secteur_id)
        wall_ref = secteur_Ref.collection("blocs").document(projet.wall_id)

    #check if the project exist
    project = firestore_async_db.collection("users").document(current_user).collection("projects").where("wall_ref", "==", wall_ref).stream()
    async for _ in project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project already exist",
        )
    
    projectRef = firestore_async_db.collection("users").document(current_user).collection("projects").document()
    await projectRef.set(
        {
            "climbingLocation_ref": cloc_Ref,
            "secteur_ref": secteur_Ref,
            "wall_ref": wall_ref,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_spraywall": projet.is_spraywall,
        }
    )

    #formulate the response
    projetResp = await get_project_data(await projectRef.get())
    projetResp["climbingLocation_ref"] = None
    projetResp["secteur_ref"] = None
    projetResp["wall_ref"] = None
    return projetResp

@app.get("/api/v1/user/me/project/", response_model=List[ProjectResp])
async def list_project(
    current_user: str = Depends(get_current_user),
):
    """
    List all the projects of the user
    """
    projets = firestore_async_db.collection("users").document(current_user).collection("projects").stream()
    if projets.__anext__ == None:
        return []

    projects_list = await asyncio.gather(*[get_project_data(projet) async for projet in projets])
    projects_list = [project for project in projects_list if project] # remove None values
    return projects_list

@app.delete("/api/v1/user/me/project/")
async def delete_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    """
    Delete a project
    """

    projectRef = firestore_async_db.collection("users").document(current_user).collection("projects").document(project_id)
    project = await projectRef.get()
    if not project.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found",
        )
    await projectRef.delete()
    return {"message": "Project deleted successfully"}