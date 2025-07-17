from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import faiss
import json
from pathlib import Path

INPUT = Path("extracted/class_norms.json")
INDEX = Path("index/class_norms.index")
META = Path("index/class_norms_meta.pkl")

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

texts = []
metadatas = []

for item in data:
    indicator = item.get("indicator", "")
    values = item.get("values", {})
    if not indicator or not values:
        continue

    # Для индекса — комбинируем индикатор + все значения
    combined = indicator + " " + " ".join([f"{k}: {v}" for k, v in values.items()])
    texts.append(combined)
    metadatas.append(item)  # <–– сохраняем всю структуру (включая values)

embeddings = model.encode(texts, convert_to_numpy=True)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

INDEX.parent.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(INDEX))

with open(META, "wb") as f:
    pickle.dump(metadatas, f)

print(f"✅ Индекс сохранён: {INDEX}")
print(f"🧠 Метаданные: {META}")
print(f"🔍 Всего в индексе: {len(metadatas)} записей")
