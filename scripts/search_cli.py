# scripts/search_cli.py
# -*- coding: utf-8 -*-
import argparse
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

QDRANT_URL = "http://127.0.0.1:6333"
QDRANT_COLLECTION = "kb"
EMB_MODEL = "intfloat/multilingual-e5-base"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("query", help="текст запроса")
    p.add_argument("--corpus", default=None, help="payload.corpus фильтр (например: norms)")
    p.add_argument("--limit", type=int, default=8, help="сколько вернуть результатов")
    p.add_argument("--debug", action="store_true", help="показать отладочную информацию")
    args = p.parse_args()

    if args.debug:
        print(f"[DEBUG] Connecting to {QDRANT_URL}, collection={QDRANT_COLLECTION}")
        print(f"[DEBUG] Model: {EMB_MODEL}")

    emb = SentenceTransformer(EMB_MODEL)
    vec = emb.encode([args.query], normalize_embeddings=True)[0]

    qf = None
    if args.corpus:
        qf = Filter(must=[FieldCondition(key="corpus", match=MatchValue(value=args.corpus))])

    c = QdrantClient(url=QDRANT_URL, check_compatibility=False)

    hits = c.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vec,
        limit=args.limit,
        query_filter=qf,
        with_payload=True,
        with_vectors=False,
    )

    if args.debug:
        print(f"[DEBUG] got {len(hits)} hits")

    if not hits:
        print("0 результатов.")
        return

    for i, h in enumerate(hits, 1):
        pl = h.payload or {}
        text = (pl.get("text") or "").replace("\n", " ")
        snippet = text[:200] + ("…" if len(text) > 200 else "")
        source = pl.get("source")
        sid = pl.get("sid")
        corpus = pl.get("corpus")
        print(f"{i}. score={h.score:.4f} | corpus={corpus} | source={source} | sid={sid}")
        print(f"   {snippet}")

if __name__ == "__main__":
    main()
