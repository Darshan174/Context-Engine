from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.user import Workspace
from app.schemas.user import WorkspaceCreate, WorkspaceRead


router = APIRouter()


@router.post(
    "/workspaces",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreate,
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceRead:
    workspace = Workspace(**payload.model_dump())
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.get("/workspaces", response_model=list[WorkspaceRead])
async def list_workspaces(
    session: AsyncSession = Depends(get_db_session),
) -> list[WorkspaceRead]:
    result = await session.scalars(select(Workspace).order_by(Workspace.created_at.desc()))
    return [WorkspaceRead.model_validate(item) for item in result]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceRead:
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return WorkspaceRead.model_validate(workspace)
