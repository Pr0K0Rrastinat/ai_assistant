# class_norms_rag.py
import faiss
import pickle
from pathlib import Path
from typing import List, Dict, Any
from model_loader import load_sentence_transformer_model  

class ClassNormsRAG:
    def __init__(
        self,
        index_path: str = "index/class_norms.index",
        meta_path: str = "index/class_norms_meta.pkl",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.model_name = model_name

        self._load_index()
        self._load_metadata()
        self._load_model()

    def _load_index(self):
        print(f"📦 Загружаем индекс: {self.index_path}")
        self.index = faiss.read_index(str(self.index_path))

    def _load_metadata(self):
        print(f"🧠 Загружаем мета-данные: {self.meta_path}")
        with open(self.meta_path, "rb") as f:
            self.metadata = pickle.load(f)
    
    def _load_model(self):
        print(f"🤖 Загружаем модель: {self.model_name}")
        self.model = load_sentence_transformer_model(self.model_name)


    def query(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        embedding = self.model.encode([text])
        distances, indices = self.index.search(embedding, top_k)

        results = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])
        return results
