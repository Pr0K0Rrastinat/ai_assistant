from pathlib import Path
from norm_rag import NormRAG

# Путь к папке, где лежит norms_checklist.json и norms_checklist.index
BASE_DIR = Path(__file__).resolve().parent

# Инициализируем RAG
rag = NormRAG(base_dir=BASE_DIR, source_file="norms_checklist_v2.json")

# Вопрос архитектора
query = "Какова минимальная высота установки эвакуационных знаков направления эвакуации?"
applies_to = None

# Запрашиваем топ-10 релевантных норм
results = rag.query(query, top_k=20, applies_to=applies_to)

print(f"\n🔍 Найдено {len(results)} норм по запросу: '{query}' и applies_to: '{applies_to}'\n")

for i, norm in enumerate(results, 1):
    print(f"{i}. 🧾 ID: {norm.get('id', '—')}")
    print(f"   📜 Текст: {norm.get('text', '')}")
    print(f"   📂 Источник: {norm.get('source', '—')}")
    print("---")
