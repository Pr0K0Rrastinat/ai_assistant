import json5
import json
import requests
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
input_path = BASE_DIR / "extracted" / "norms.json"
output_path = BASE_DIR / "extracted" / "norms_checklist.json"

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def generate_checklist_prompt(norms):
    norm_texts = "\n".join([f"{i+1}. [{n['id']}] {n['text']}" for i, n in enumerate(norms)])
    return f"""
Ты строительный эксперт. Преобразуй нормативы в структурированный чек-лист для автоматической проверки проектной документации.

Для каждого норматива верни словарь с такими ключами:
- id
- text
- applies_to
- condition
- requirement
- check

Пример:
- id: "4.2.6"
  applies_to: ["лоджия", "балкон"]
  text: "4.2.6 Ограждения лоджий..."
  condition: "здание ≥ 3 этажей"
  requirement: "материал = негорючий"
  check: "если лоджия в здании ≥ 3 этажей, материал должен быть негорючим"

Вот нормативы:
{norm_texts}

Верни JSON или YAML без пояснений.
"""

def create_check_list_with_model(prompt, model_name="gemma3"):
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model_name,
        "prompt": prompt,
        "stream": False
    })
    return response.json().get("response", "")

def clean_json_like_text(text):
    # Убираем ```json ``` или Markdown-подобные обертки
    text = text.strip("` \n")

    # Обрезаем до начала структуры
    json_start = text.find("[")
    if json_start == -1:
        json_start = text.find("{")
    if json_start == -1:
        return text  # fallback

    return text[json_start:]

def save_progress(safe_list, path):
    with open(path, "w", encoding="utf-8") as out:
        json.dump(safe_list, out, ensure_ascii=False, indent=2)

def main():
    with open(input_path, encoding="utf-8") as f:
        norms = json.load(f)

    if output_path.exists():
        with open(output_path, encoding="utf-8") as out:
            checklist = json.load(out)
        print(f"📥 Загружено {len(checklist)} норм из предыдущего прогона.")
    else:
        checklist = []

    output_path.parent.mkdir(parents=True, exist_ok=True)

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
            parsed = json5.loads(cleaned)

            if isinstance(parsed, list):
                checklist.extend(parsed)
            else:
                checklist.append(parsed)

            save_progress(checklist, output_path)
            print(f"💾 Прогресс сохранён после чанка {i}. Всего норм: {len(checklist)}")

        except Exception as e:
            print(f"❌ Ошибка разбора чанка {i}: {e}")
            print("⚠️ Ответ:\n", raw_response[:800])
            continue

    print(f"\n✅ Чеклист из {len(checklist)} норм сохранён в: {output_path}")

if __name__ == "__main__":
    main()
