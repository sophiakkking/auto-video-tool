"""RAG 内部模块（PRD 5.4 / 技术设计 §7）— Phase 0 实现

- 入库：解析 → 切块(300–800 tokens, 15% 重叠) → Embedding → pgvector + FTS (KB-1)
- 检索：混合检索（向量 + BM25）+ 时效降权，top-k 5–10 (KB-2/7)
- 引用溯源：chunk 携带来源元数据 (KB-3)
"""


def ingest_document(document_id: str, text: str) -> int:
    """解析文档文本，切块并向量化；返回 chunk 数"""
    raise NotImplementedError("Phase 0: 接入解析/切块/Embedding 管线")


def retrieve(
    query: str,
    workspace_id: str,
    top_k: int = 8,
    freshness_weight: float = 1.0,
) -> list[dict]:
    """返回 [{text, doc_id, meta, freshness, score}]"""
    raise NotImplementedError("Phase 0: 混合检索 + rerank（可选）")
