from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import faiss
import json
from pathlib import Path

INPUT = Path("extracted/new_class_norms_merged.json")
INDEX = Path("index/class_norms.index")
META = Path("index/class_norms_meta.pkl")

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer  # (можно удалить, если не используешь)
import pickle
import faiss
import json
from pathlib import Path
def guess_room_type(indicator, values_dict):
    text = indicator.lower() + " " + " ".join(values_dict.values()).lower()

    if any(word in text for word in ["кухня", "плита", "приготовление пищи"]):
        return "кухня"
    if any(word in text for word in ["душ", "душевая", "санузел", "сушка", "туалет", "умывальник", "унитаз"]):
        return "санузел"
    if any(word in text for word in ["гардероб", "шкаф", "одежда", "раздевалка"]):
        return "гардеробная"
    if any(word in text for word in ["комната", "жилая", "спальня", "гостиная"]):
        return "жилая комната"
    if any(word in text for word in ["балкон", "лоджия"]):
        return "балкон"
    return "помещение"

def build_class_norms_index(input_json: Path):
    output_dir = Path("extracted/")
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    texts = []
    metadatas = []
    skipped = 0

    for item in data:
        indicator = item.get("indicator", "")
        values = item.get("values", {})
        domain = item.get("domain", "")
        source = item.get("source", "")
        full_id = item.get("full_id", "")

        if not indicator or not values:
            skipped += 1
            continue

        room_type = guess_room_type(indicator, values)

        combined = " ".join([
            guess_room_type(indicator, values),
            indicator,
            " ".join([f"{k} {v}" for k, v in values.items()]),
            domain,
            source,
            full_id
        ])


        texts.append(combined)
        metadatas.append(item)

    print(f"❌ Пропущено: {skipped}")
    print(f"✅ Добавлено: {len(metadatas)}")

    embeddings = model.encode(texts, convert_to_numpy=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "class_norms_merged.index"
    meta_path = output_dir / "class_norms_merged.pkl"

    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump(metadatas, f)

    print(f"✅ Индекс сохранён: {index_path}")
    print(f"🧠 Метаданные: {meta_path}")
    print(f"🔍 Всего в индексе: {len(metadatas)} записей")
# Пример вызова:
#build_class_norms_index(INPUT)
