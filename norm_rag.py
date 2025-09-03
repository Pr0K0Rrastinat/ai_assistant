import faiss
import json
import numpy as np
from pathlib import Path
from model_loader import load_sentence_transformer_model
from difflib import SequenceMatcher
import torch

# 🔁 Словарь синонимов
ROOM_SYNONYMS = {
    "гостиная": "жилая комната",
    "спальня": "жилая комната",
    "детская": "жилая комната",
    "кабинет": "жилая комната",
    "холл": "прихожая",
    "прихожая": "прихожая",
    "санузел": "туалет",
    "с.у": "туалет",
    "ванная": "туалет",
    "уборная": "туалет",
    "туалет": "туалет",
    "кладовка": "кладовая",
    "гардероб": "кладовая",
    "кухня-гостиная": "кухня",
    "кухня-ниша": "кухня",
    "кухня": "кухня",
    "лоджия": "балкон",
    "балкон": "балкон",
    "терраса": "балкон"
    # Можно дополнять
}

def normalize_room_type(name: str) -> str:
    name = name.lower().strip()
    return ROOM_SYNONYMS.get(name, name)

def extract_text(value) -> str:
    if isinstance(value, str):
        return value.lower()
    elif isinstance(value, dict):
        return value.get("text", "").lower()
    elif isinstance(value, list):
        return " ".join(str(v).lower() for v in value if v)
    return ""

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


class NormRAG:
    def __init__(self, base_dir: Path, source_file="norms_checklist_merged.json"):
        self.model = load_sentence_transformer_model()
        self.norms_path = base_dir / "index" / source_file
        self.index_path = base_dir / "index" / (Path(source_file).stem + ".index")

        with open(self.norms_path, "r", encoding="utf-8") as f:
            self.norms = json.load(f)

        self.index = faiss.read_index(str(self.index_path))

    def query(self, text: str, top_k=32, applies_to: str = None,domain: str = None,source: str = None):
        if domain == "- Не выбрано -":
            domain = None
        query_vec = self.model.encode([text])
        D, I = self.index.search(np.array(query_vec), top_k * 2)
        candidates = [self.norms[int(i)] for i in I[0] if 0 <= i < len(self.norms)]

        if source:
            candidates = [
                n for n in candidates
                if any(
                    d.strip().lower() in [dd.strip().lower() for dd in n.get("source", "").split(",")]
                    for d in source
                )
            ]
        if applies_to:
            applies_vec = self.model.encode([applies_to])[0]
            scored = []
            for norm in candidates:
                applies = norm.get("applies_to", [])
                if isinstance(applies, str):
                    applies = [applies]
                applies = [a for a in applies if isinstance(a, str)]
                if not applies:
                    continue

                apply_vecs = self.model.encode([a.lower() for a in applies])
                best_score = max(np.dot(vec, applies_vec) for vec in apply_vecs)
                if best_score > 0.6:  # порог
                    scored.append(norm)

            if scored:
                candidates = scored
        if domain:
            candidates = [
                n for n in candidates
                if any(
                    d.strip().lower() in [dd.strip().lower() for dd in n.get("domain", "").split(",")]
                    for d in domain
                )
            ]

      
        return candidates[:top_k]
    
    def _query_class_norms(self, question: str, top_k=12):
        if not self.class_index or not self.class_meta:
            return []

        query_vec = self.model.encode([question])
        D, I = self.class_index.search(query_vec, top_k)
        results = []
        for i in I[0]:
            if i < len(self.class_meta):
                results.append(self.class_meta[i])
        return results
