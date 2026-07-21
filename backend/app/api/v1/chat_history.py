import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import (
    ChatMessageList,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionList,
    ChatSessionOut,
    ChatSessionUpdate,
)
from app.services import chat_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/history", tags=["chat_history"])


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
async def create_chat_session(
    body: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session = await chat_history_service.create_session(db, title=body.title)
    return chat_history_service.session_to_dict(session)


@router.get("/sessions", response_model=ChatSessionList)
async def list_chat_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    sessions = await chat_history_service.list_sessions(db, skip=skip, limit=limit, search=search)
    total = await chat_history_service.count_sessions(db, search=search)
    return {"total": total, "sessions": [chat_history_service.session_to_dict(s) for s in sessions]}


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await chat_history_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_history_service.session_to_dict(session)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
async def update_chat_session(
    session_id: str,
    body: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    session = await chat_history_service.update_session(
        db, session_id, title=body.title, pinned=body.pinned
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_history_service.session_to_dict(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    deleted = await chat_history_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageList)
async def list_chat_messages(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    session = await chat_history_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await chat_history_service.get_messages(db, session_id, skip=skip, limit=limit)
    total = await chat_history_service.count_messages(db, session_id)
    out = []
    for m in messages:
        d = chat_history_service.message_to_dict(m)
        if d["response"]:
            d["response"]["latencies"] = d["response"].get("latencies") or {}
        out.append(ChatMessageOut(**d))
    return {"total": total, "messages": out}


@router.delete("/sessions/{session_id}/messages", status_code=204)
async def clear_chat_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await chat_history_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await chat_history_service.delete_all_messages(db, session_id)
