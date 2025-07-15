# scripts/rebuild_faiss_index.py

import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# === Пути ===
BASE_DIR = Path(__file__).resolve().parent.parent
NORM_PATH = BASE_DIR / "extracted" / "norms_checklist.json"
INDEX_PATH = BASE_DIR / "index" / "norms_checklist.index"

# === Модель ===
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# === Загрузка норм ===
with open(NORM_PATH, encoding="utf-8") as f:
    norms = json.load(f)

# === Получение текстов для индексации ===
texts = [n["text"] for n in norms if "text" in n and n["text"]]

# === Кодируем тексты ===
embeddings = model.encode(texts, show_progress_bar=True)

# === Создание и сохранение индекса ===
embedding_dim = embeddings.shape[1]
index = faiss.IndexFlatL2(embedding_dim)
index.add(np.array(embeddings).astype("float32"))

INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(INDEX_PATH))

print(f"✅ FAISS-индекс создан и сохранён: {INDEX_PATH}")


def rebuild_index_from_norms(norms_path):
    import faiss
    from sentence_transformers import SentenceTransformer
    with open(norms_path, encoding="utf-8") as f:
        norms = json.load(f)
    texts = [n["text"] for n in norms if "text" in n and n["text"]]
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = model.encode(texts, show_progress_bar=True)
    embedding_dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(embedding_dim)
    index.add(embeddings.astype("float32"))
    index_path = Path("index/norms_checklist.index")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
