# build_index_v2.py

import os
import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent  # поднимаемся на 1 уровень выше
SOURCE = BASE_DIR / "extracted" / "norms_checklist.json"
INDEX_PATH = BASE_DIR / "index" / "norms_checklist_v2.index"
os.makedirs(INDEX_PATH.parent, exist_ok=True)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Загрузка норм
with open(SOURCE, encoding="utf-8") as f:
    norms = json.load(f)

# Формируем комбинированный текст
def combine_fields(norm):
    fields = [norm.get("text"), norm.get("requirement"), norm.get("check")]
    fields = [str(f) for f in fields if isinstance(f, str)]
    return " ".join(fields).strip()

combined_texts = [combine_fields(n) for n in norms]

combined_texts = [combine_fields(n) for n in norms]
vectors = model.encode(combined_texts, show_progress_bar=True)

# Создание индекса
index = faiss.IndexFlatL2(vectors.shape[1])
index.add(np.array(vectors).astype("float32"))

# Сохраняем
faiss.write_index(index, str(INDEX_PATH))

# Сохраняем норму с комбинированным полем
for norm, text in zip(norms, combined_texts):
    norm["combined_text"] = text

with open(BASE_DIR / "index" / "norms_checklist_v2.json", "w", encoding="utf-8") as f:
    json.dump(norms, f, ensure_ascii=False, indent=2)

print("✅ Новый индекс построен и сохранён.")
