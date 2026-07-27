from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_project_registry
from app.projects.registry import ProjectConfig, ProjectRegistry


router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    id: str
    code: str
    name: str
    default_branch: str
    default_runtime_profile: str
    allowed_runtime_profiles: list[str]


def to_response(project: ProjectConfig) -> ProjectResponse:
    return ProjectResponse(
        id=project.physical_id_string,
        code=project.id,
        name=project.name,
        default_branch=project.repository.default_branch,
        default_runtime_profile=project.runtime.default_profile,
        allowed_runtime_profiles=project.runtime.allowed_profiles,
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    registry: ProjectRegistry = Depends(get_project_registry),
) -> list[ProjectResponse]:
    return [to_response(project) for project in registry.list()]


@router.get("/{project_reference}", response_model=ProjectResponse)
def get_project(
    project_reference: str,
    registry: ProjectRegistry = Depends(get_project_registry),
) -> ProjectResponse:
    project = registry.resolve(project_reference)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return to_response(project)
