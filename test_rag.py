from class_norms_rag import ClassNormsRAG

rag = ClassNormsRAG()

while True:
    query = input("\n🔎 Введите запрос (или 'exit'): ").strip()
    if query.lower() in {"exit", "quit"}:
        break

    results = rag.query(query)
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
