import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import trace_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["traces"])


@router.get("/traces")
async def list_traces(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    traces = await trace_service.list_traces(db, skip=skip, limit=limit)
    total = await trace_service.count_traces(db)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "traces": [trace_service.trace_to_dict(t) for t in traces],
    }


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
):
    trace = await trace_service.get_trace(db, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace_service.trace_to_dict(trace)


@router.get("/traces/export/json")
async def export_traces_json(
    db: AsyncSession = Depends(get_db),
):
    traces = await trace_service.list_traces(db, skip=0, limit=10000)
    data = [trace_service.trace_to_dict(t) for t in traces]
    return PlainTextResponse(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=sentinelrag_traces.json"},
    )


@router.get("/traces/export/csv")
async def export_traces_csv(
    db: AsyncSession = Depends(get_db),
):
    traces = await trace_service.list_traces(db, skip=0, limit=10000)
    data = [trace_service.trace_to_dict(t) for t in traces]
    csv_content = trace_service.export_traces_csv(data)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sentinelrag_traces.csv"},
    )


@router.get("/traces/export/markdown")
async def export_traces_markdown(
    db: AsyncSession = Depends(get_db),
):
    traces = await trace_service.list_traces(db, skip=0, limit=10000)
    data = [trace_service.trace_to_dict(t) for t in traces]
    md_content = trace_service.export_traces_markdown(data)
    return PlainTextResponse(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=sentinelrag_decision_report.md"},
    )
