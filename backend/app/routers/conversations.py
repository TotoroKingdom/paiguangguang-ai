from datetime import timezone

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import settings
from app.modules.identity.user_service import UserIdentityService
from app.owner import get_owner_id, require_json_request, verified_owner_id
from app.repositories import OwnerScope
from app.schemas import (
    ConversationCreate,
    ConversationListResponse,
    ConversationRename,
    ConversationResponse,
    ConversationSummary,
    MessagePatch,
    MessageResponse,
    TurnCreate,
    TurnResponse,
)
from app.services import ConversationService, decode_cursor, encode_cursor

router = APIRouter(tags=["conversations"])


def conversation_scope(
    request: Request, response: Response, session: Session
) -> OwnerScope:
    token = request.cookies.get(settings.user_session_cookie_name)
    principal = UserIdentityService(session).resolve_session(token)
    if token and principal is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Session expired or revoked")
    if principal is not None:
        if principal.user.status != "ACTIVE" or principal.session.scope != "FULL":
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Account is not active")
        if request.method in {"POST", "PATCH", "DELETE"}:
            from app.modules.identity.dependencies import require_user_csrf

            require_user_csrf(request, principal)
        return OwnerScope(
            owner_id=verified_owner_id(request) or "",
            user_id=principal.user.id,
        )
    return OwnerScope(owner_id=get_owner_id(request, response))


@router.post("/conversations", response_model=ConversationSummary, status_code=201)
def create_conversation(
    request: Request,
    response: Response,
    payload: ConversationCreate | None = None,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    scope = conversation_scope(request, response, session)
    return ConversationService(session).create(
        scope,
        payload.title if payload else "新对话",
        payload.migrationKey if payload else None,
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    request: Request,
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    q: str = Query(default="", max_length=80),
    session: Session = Depends(get_db),
):
    scope = conversation_scope(request, response, session)
    cursor_time, cursor_id = decode_cursor(cursor) if cursor else (None, None)
    items = ConversationService(session).repository.list(
        scope, limit + 1, cursor_time, cursor_id, q.strip()
    )
    next_cursor = encode_cursor(items[limit - 1]) if len(items) > limit else None
    return ConversationListResponse(
        items=[
            ConversationSummary(
                id=item.id,
                title=item.title,
                createdAt=item.created_at.replace(tzinfo=timezone.utc),
                updatedAt=item.updated_at.replace(tzinfo=timezone.utc),
                version=item.version,
            )
            for item in items[:limit]
        ],
        nextCursor=next_cursor,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str, request: Request, response: Response, session: Session = Depends(get_db)
):
    scope = conversation_scope(request, response, session)
    return ConversationService(session).detail(scope, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(
    conversation_id: str,
    payload: ConversationRename,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    scope = conversation_scope(request, response, session)
    return ConversationService(session).rename(
        scope, conversation_id, payload.title, payload.version
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str, request: Request, response: Response, session: Session = Depends(get_db)
):
    scope = conversation_scope(request, response, session)
    ConversationService(session).delete(scope, conversation_id)


@router.post("/conversations/{conversation_id}/turns", response_model=TurnResponse, status_code=201)
def create_turn(
    conversation_id: str,
    payload: TurnCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    scope = conversation_scope(request, response, session)
    return ConversationService(session).create_turn(scope, conversation_id, payload)


@router.patch(
    "/conversations/{conversation_id}/messages/{message_id}", response_model=MessageResponse
)
def patch_message(
    conversation_id: str,
    message_id: str,
    payload: MessagePatch,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
):
    require_json_request(request)
    scope = conversation_scope(request, response, session)
    return ConversationService(session).patch_message(
        scope, conversation_id, message_id, payload
    )

