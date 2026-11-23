"""知识库路由 — RAG 内部模块（PRD 5.4）"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import KbDocument
from .jobs import _demo_workspace_id

router = APIRouter(prefix="/v1/kb", tags=["kb"])


class DocumentCreate(BaseModel):
    title: str
    doc_type: str = "file"
    source_url: str | None = None


@router.post("/documents", status_code=201)
async def add_document(payload: DocumentCreate, db: AsyncSession = Depends(get_db)):
    """文档入库（仅当用户显式勾选「存入知识库」才调用，KB-9）"""
    doc = KbDocument(
        workspace_id=await _demo_workspace_id(db),
        title=payload.title,
        doc_type=payload.doc_type,
        source_url=payload.source_url,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    # TODO Phase 0: 入队切块 + Embedding 索引（技术设计 §7.1）
    return {"id": doc.id, "status": doc.status}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """删除文档及全部 chunks（KB-9 可随时删除）"""
    doc = await db.get(KbDocument, document_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    await db.delete(doc)  # 级联删除 chunks
    await db.commit()
    return {"deleted": document_id}


@router.get("/retrieve", status_code=501)
async def retrieve(query: str):
    """内部检索：query → top-k chunks + 引用 (KB-2)。仅内部服务调用，不对外。"""
    raise HTTPException(501, "Phase 0 实现：混合检索（向量 + BM25）+ 时效降权（技术设计 §7.2）")
