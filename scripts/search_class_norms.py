#search_class_norms
import faiss
import pickle
import json
import torch
from model_loader import load_sentence_transformer_model
INDEX_PATH = "index/class_norms_merged.index"
META_PATH = "index/class_norms_merged.pkl"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Загружаем индекс и мета-данные
print("📥 Загружаем индекс и модель...")
index = faiss.read_index(INDEX_PATH)
with open(META_PATH, "rb") as f:
    metadata = pickle.load(f)

model = load_sentence_transformer_model()

def search(query, top_k=5, sources: list[str] = None):
    embedding = model.encode([query])
    distances, indices = index.search(embedding, top_k * 5)  # запас для фильтрации

    results = []
    for idx in indices[0]:
        if idx < len(metadata):
            item = metadata[idx]
            item_source = item.get("source", "").strip()

            if sources:
                if not any(item_source == s.strip() for s in sources):
                    continue

            results.append(item)
            if len(results) >= top_k:
                break
    return results

if __name__ == "__main__":
    while True:
        query = input("\n🔎 Введите запрос (или 'exit'): ").strip()
        if query.lower() in {"exit", "quit"}:
            break

        results = search(query)
        if not results:
            print("😕 Ничего не найдено.")
        else:
            print("\n📌 Найдено:")
            for i, item in enumerate(results, 1):
                indicator = item.get("indicator", "❓ Без названия")
                print(f"\n{i}. 🧾 {indicator}")

                values = item.get("values")
                if isinstance(values, dict):
                    for cls, value in values.items():
                        print(f"   - {cls}: {value}")
                else:
                    print("   ⚠️ Нет данных 'values' в этом элементе.")

