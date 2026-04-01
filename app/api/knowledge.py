from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.knowledge import (
    ComponentCreate,
    ComponentRead,
    ComponentSourceRead,
    ComponentUpdate,
    KnowledgeModelCreate,
    KnowledgeModelDetail,
    KnowledgeModelRead,
    RelationshipCreate,
    RelationshipRead,
)
from app.services.knowledge_service import (
    InvalidRequestError,
    KnowledgeService,
    ResourceConflictError,
    ResourceNotFoundError,
)


router = APIRouter()


def get_knowledge_service(session: AsyncSession = Depends(get_db_session)) -> KnowledgeService:
    return KnowledgeService(session)


@router.post(
    "/models",
    response_model=KnowledgeModelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    payload: KnowledgeModelCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeModelRead:
    try:
        model = await service.create_model(**payload.model_dump())
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return KnowledgeModelRead.model_validate(model)


@router.get("/models", response_model=list[KnowledgeModelRead])
async def list_models(
    workspace_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[KnowledgeModelRead]:
    try:
        models = await service.list_models_for_workspace(workspace_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [KnowledgeModelRead.model_validate(model) for model in models]


@router.get("/models/{model_id}", response_model=KnowledgeModelDetail)
async def get_model(
    model_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeModelDetail:
    try:
        model = await service.get_model(model_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return KnowledgeModelDetail.model_validate(model)


@router.get("/components/{component_id}", response_model=ComponentRead)
async def get_component(
    component_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ComponentRead:
    try:
        component = await service.get_component(component_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ComponentRead.model_validate(component)


@router.post(
    "/models/{model_id}/components",
    response_model=ComponentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_component(
    model_id: UUID,
    payload: ComponentCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ComponentRead:
    try:
        component = await service.add_component(model_id, **payload.model_dump())
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ComponentRead.model_validate(component)


@router.patch("/components/{component_id}", response_model=ComponentRead)
async def update_component(
    component_id: UUID,
    payload: ComponentUpdate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ComponentRead:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    try:
        component = await service.update_component(component_id, **update_data)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ComponentRead.model_validate(component)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(
    component_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Response:
    try:
        await service.delete_component(component_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/relationships",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    payload: RelationshipCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> RelationshipRead:
    try:
        relationship = await service.create_relationship(**payload.model_dump())
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return RelationshipRead.model_validate(relationship)


@router.get("/models/{model_id}/relationships", response_model=list[RelationshipRead])
async def get_model_relationships(
    model_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[RelationshipRead]:
    try:
        relationships = await service.get_model_relationships(model_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [RelationshipRead.model_validate(item) for item in relationships]


@router.get("/components/{component_id}/sources", response_model=list[ComponentSourceRead])
async def get_component_sources(
    component_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[ComponentSourceRead]:
    try:
        links = await service.get_component_sources(component_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [
        ComponentSourceRead(
            source_document_id=link.source_document_id,
            connector_type=link.source_document.connector_type.value,
            external_id=link.source_document.external_id,
            label=link.source_document.label,
            source_url=link.source_document.source_url,
            author=link.source_document.author,
            ingested_at=link.source_document.ingested_at,
            extraction_context=link.extraction_context,
            extractor_name=link.extractor_name,
            extractor_kind=link.extractor_kind,
            extractor_schema_version=link.extractor_schema_version,
        )
        for link in links
    ]


@router.get("/components/{component_id}/relationships", response_model=list[RelationshipRead])
async def get_component_relationships(
    component_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[RelationshipRead]:
    try:
        relationships = await service.get_component_relationships(component_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [RelationshipRead.model_validate(item) for item in relationships]
