import faiss
import pickle
from pathlib import Path

# Пути к файлам
index_path = Path("extracted/class_norms_merged.index")
meta_path = Path("extracted/class_norms_merged.pkl")

# Загрузка индекса
index = faiss.read_index(str(index_path))
print(f"✅ Индекс загружен: {index.ntotal} записей")

# Загрузка метаданных
with open(meta_path, "rb") as f:
    metadata = pickle.load(f)

# Пример: показать первые 3 записи
for i, item in enumerate(metadata[:3]):
    print(f"\n--- Запись {i+1} ---")
    print(f"📌 Indicator: {item.get('indicator')}")
    print(f"📊 Values: {item.get('values')}")
    print(f"📂 Source: {item.get('source')}")
    print(f"🏷️ Domain: {item.get('domain')}")
    print(f"🆔 Full ID: {item.get('full_id')}")
    print(f"🆔 Room type: {item.get('reoom_type')}")

