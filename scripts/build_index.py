# scripts/build_index.py
import os
import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
NORM_FILE = BASE_DIR / "extracted" / "norms.json"
INDEX_FILE = BASE_DIR / "index" / "norms.index"

os.makedirs(INDEX_FILE.parent, exist_ok=True)

# Загрузка норм
with open(NORM_FILE, "r", encoding="utf-8") as f:
    norms = json.load(f)

# Эмбеддер (универсальный)
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Формируем текст для индексации
texts = [item["text"] for item in norms]
vectors = model.encode(texts, show_progress_bar=True)

# Создаём FAISS индекс
index = faiss.IndexFlatL2(len(vectors[0]))
index.add(np.array(vectors))

# Сохраняем
faiss.write_index(index, str(INDEX_FILE))

# Сохраняем тексты отдельно
with open(INDEX_FILE.with_suffix(".json"), "w", encoding="utf-8") as f:
    json.dump(norms, f, ensure_ascii=False, indent=2)

print(f"✅ Индекс создан: {INDEX_FILE}")
