import json5
import json
import requests
import time
from pathlib import Path

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def generate_checklist_prompt(norms):
    norm_texts = "\n".join([f"{i+1}. [{n['id']}] {n['text']}" for i, n in enumerate(norms)])
    return f"""
    Ты строительный эксперт. Не пиши пояснений. Не пиши заголовков. Не пиши вводных фраз. Просто верни JSON-массив с нормами.

    Для каждой нормы укажи:
    - id
    - text
    - applies_to
    - condition
    - requirement
    - check
    - domain (например: "архитектура", "инженерия", "пожарная безопасность" и т.п.)

    Пример:
    [
    {{
        "id": "4.2.6",
        "applies_to": ["лоджия", "балкон"],
        "text": "4.2.6 Ограждения лоджий...",
        "condition": "здание ≥ 3 этажей",
        "requirement": "материал = негорючий",
        "check": "если лоджия в здании ≥ 3 этажей, материал должен быть негорючим",
        "domain": "пожарная безопасность"
    }}
    ]

    Вот нормативы:
    {norm_texts}
    """

def create_check_list_with_model(prompt, model_name="mistral"):
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model_name,
        "prompt": prompt,
        "stream": False
    })
    return response.json().get("response", "")

def clean_json_like_text(text):
    text = text.strip("` \n")
    json_start = text.find("[")
    if json_start == -1:
        json_start = text.find("{")
    if json_start == -1:
        return text
    return text[json_start:]

def convert_norms_to_checklist(norms, output_json: Path):

    if output_json.exists():
        with open(output_json, encoding="utf-8") as out:
            checklist = json.load(out)
        print(f"📥 Загружено {len(checklist)} норм из предыдущего прогона.")
    else:
        checklist = []

    existing_ids = {item.get("full_id") for item in checklist if "full_id" in item}
    print(f"🚀 Всего к обработке: {len(norms)} норм")
    print(f"▶️ Первая норма: {norms[0].get('full_id', '???')}")

    output_json.parent.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(chunked(norms, 5), start=1):
        prompt = generate_checklist_prompt(chunk)
        raw_response = create_check_list_with_model(prompt)
    
        if not raw_response.strip() or "❌" in raw_response or len(raw_response.strip()) < 20:
            print(f"⚠️ Пустой или ошибочный ответ на чанке {i}. Повтор через 3 сек...")
            time.sleep(3)
            raw_response = create_check_list_with_model(prompt)

        time.sleep(1)

        try:
            cleaned = clean_json_like_text(raw_response)
            if not cleaned.strip().startswith("[") and not cleaned.strip().startswith("{"):
                print(f"⚠️ Ответ на чанке {i} не похож на JSON. Пропускаем.")
                with open(f"debug_response_chunk_{i}.txt", "w", encoding="utf-8") as f:
                    f.write(raw_response)
                continue

            parsed = json5.loads(cleaned)
            
            enriched = []
            for j, item in enumerate(parsed if isinstance(parsed, list) else [parsed]):
                if j < len(chunk):
                    source = chunk[j].get("source", "")
                    item["source"] = source
                    item["full_id"] = f"{source}:{item['id']}" if "id" in item and source else ""
                enriched.append(item)

            new_items = [item for item in enriched if item.get("full_id") not in existing_ids]
            if not new_items:
                print(f"⏭️ Все {len(enriched)} норм уже есть. Пропускаем.")
                continue

            checklist.extend(new_items)
            existing_ids.update(item["full_id"] for item in new_items)
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(checklist, f, ensure_ascii=False, indent=2)

            print(f"💾 Прогресс сохранён после чанка {i}. Всего норм: {len(checklist)}")

        except Exception as e:
            print(f"❌ Ошибка разбора чанка {i}: {e}")
            print("⚠️ Ответ:\n", raw_response[:800])
            continue

    print(f"\n✅ Чеклист из {len(checklist)} норм сохранён в: {output_json}")
