"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_logs: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
MIN_SCORE = 0.03
_COLLECTION_NAME = "day09_docs"
_EMBED_FN = None


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    global _EMBED_FN
    if _EMBED_FN is not None:
        return _EMBED_FN

    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Ưu tiên SentenceTransformer trước để tránh lệch embedding space
    # nếu collection đã được index bằng all-MiniLM-L6-v2.
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed(text: str) -> list:
            return model.encode([text], normalize_embeddings=True)[0].tolist()

        _EMBED_FN = embed
        return _EMBED_FN
    except Exception:
        pass

    # Fallback sang OpenAI nếu môi trường không có sentence-transformers.
    # Lưu ý: collection phải được build bằng cùng embedding model thì retrieval mới chuẩn.
    if openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_api_key)

            def embed(text: str) -> list:
                resp = client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small",
                )
                return resp.data[0].embedding

            _EMBED_FN = embed
            return _EMBED_FN
        except Exception:
            pass

    # Fallback cuối cùng cho local smoke test.
    import random

    def embed(text: str) -> list:
        random.seed(abs(hash(text)) % (2**32))
        return [random.random() for _ in range(384)]

    print("⚠️  WARNING: Using pseudo-random embeddings (test only).")
    _EMBED_FN = embed
    return _EMBED_FN



def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb

    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_paths = [
        os.path.join(os.getcwd(), "chroma_db"),
        os.path.join(current_dir, "chroma_db"),
        os.path.join(current_dir, "..", "chroma_db"),
    ]

    db_path = None
    for path in candidate_paths:
        if os.path.isdir(path):
            db_path = os.path.abspath(path)
            break

    if db_path is None:
        db_path = os.path.abspath(os.path.join(current_dir, "..", "chroma_db"))

    client = chromadb.PersistentClient(path=db_path)

    try:
        collection = client.get_collection(_COLLECTION_NAME)
    except Exception:
        collection = client.get_or_create_collection(
            _COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print(
            f"⚠️  Collection '{_COLLECTION_NAME}' chưa có data ở {db_path}. "
            "Chạy index script trong README trước."
        )

    return collection



def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    TODO Sprint 2: Implement phần này.
    - Dùng _get_embedding_fn() để embed query
    - Query collection với n_results=top_k
    - Format result thành list of dict

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    query = (query or "").strip()
    if not query:
        return []

    try:
        collection = _get_collection()
        if hasattr(collection, "count") and collection.count() == 0:
            print(f"⚠️  Collection '{_COLLECTION_NAME}' đang rỗng.")
            return []

        embed = _get_embedding_fn()
        query_embedding = embed(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, int(top_k)),
            include=["documents", "distances", "metadatas"],
        )

        documents = (results.get("documents") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        chunks = []
        for doc, dist, meta in zip(documents, distances, metadatas):
            if not doc:
                continue

            meta = meta or {}
            try:
                score = round(max(0.0, 1.0 - float(dist)), 4)
            except Exception:
                score = 0.0

            chunks.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": score,
                    "metadata": meta,
                }
            )

        filtered = [c for c in chunks if c["score"] >= MIN_SCORE]
        return filtered if filtered else chunks[:1]

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        return []



def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)
        sources = sorted(list({c["source"] for c in chunks}))

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks" )
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
