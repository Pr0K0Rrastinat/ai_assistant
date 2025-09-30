import requests
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from scripts.extrect_object_category import group_norms_by_category

def dedup_text_norms(norms):
    seen = set()
    deduped = []
    for norm in norms:
        text = norm.get("text", "")
        full_id = norm.get("full_id", "")
        key = f"{text}:{full_id}"
        if text and key not in seen:
            deduped.append(norm)
            seen.add(key)
    return deduped


def dedup_table_norms(norms):
    seen = set()
    deduped = []
    for norm in norms:
        indicator = norm.get("indicator", "")
        values_str = json.dumps(norm.get("values", {}), ensure_ascii=False)
        full_id = norm.get("full_id", "")
        key = f"{indicator}:{values_str}:{full_id}"
        if key not in seen:
            deduped.append(norm)
            seen.add(key)
    return deduped


def split_into_batches(all_norms, batch_size):
    for i in range(0, len(all_norms), batch_size):
        yield all_norms[i:i + batch_size]

def format_table_norm(norm):
    indicator = norm.get("indicator", "—")
    values = norm.get("values", {})
    result = f"◾ {indicator}:\n"
    for cls, val in values.items():
        result += f"   - {cls}: {val}\n"
    return result.strip()

def format_text_norm(norm):
    text = norm.get("text", "").strip()
    norm = norm.get("full_id","").strip()
    return f"{norm}- {text}"

def clean_llm_output(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def generate_combined_prompt(text_norms, table_norms, user_question):
    parts = []

    if table_norms:
        table_part = "\n\n".join([format_table_norm(n) for n in table_norms])
        parts.append(f"📊 Табличные нормы:\n{table_part}")

    if text_norms:
        text_part = "\n".join([format_text_norm(n) for n in text_norms])
        parts.append(f"📜 Текстовые нормы:\n{text_part}")

    prompt = (
        f"Вопрос архитектора:\n{user_question.strip()}\n\n" +
        "Нормы на которые ты должен проверить"+
        "\n\n".join(parts) +
        "\n\nНа основе этих нормативов,полезный и понятный ответ архитектору на русском языке.КРИТИЧНО ВАЖНО  ИСПОЛЬЗУЙ ТОЛЬКО представленные нормы не бери данные со своей баззы "
    )

    return prompt

def generate_categorized_prompt(text_norms, table_norms, user_question,sourse):
    prompt_parts = [f"Вопрос архитектора:\n{user_question.strip()}"]

    if text_norms:
        grouped_text = group_norms_by_category(text_norms)
        for category, norms in grouped_text.items():
            formatted = "\n".join([format_text_norm(n) for n in norms])
            prompt_parts.append(f"📜 {category} (Текстовые нормы):\n{formatted}")

    if table_norms:
        grouped_table = group_norms_by_category(table_norms)
        for category, norms in grouped_table.items():
            formatted = "\n\n".join([format_table_norm(n) for n in norms])
            prompt_parts.append(f"📊 {category} (Табличные нормы):\n{formatted}")

    prompt_parts.append(f"\nНа основе только этих нормативов, дай краткий, полезный и понятный ответ архитектору на русском языке.Документ который ты читаешь {sourse}.КРИТИЧНО ВАЖНО ИСПОЛЬЗУЙ ТОЛЬКО представленные нормы не бери данные со своей базы. Там указывается полный пункт к нормам используй их когда будешь писать ответ")
    return "\n\n".join(prompt_parts)



"""def summarize_llm_batches(responses, question, model_name="gemma"):
    if not responses:
        return "❗ Нет промежуточных ответов для суммирования."

    combined = "\n\n".join([f"Ответ {i+1}:\n{resp}" for i, resp in enumerate(responses)])
    prompt = (
    f"Ты — помощник архитектора. Если что категория и класс синонимы. Если в вопросе спршивают насчет категорий и класс то считай что это одно и тоже Отвечай кратко, строго по нормам.\n\n"
    f"Вопрос:\n{question.strip()}\n\n"
    f"{combined}\n\n"
    "**📌 Финальный ответ:**"
)



    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return response.json().get("response", "❌ Нет финального ответа.")
    except Exception as e:
        return f"❌ Ошибка при финальном суммировании: {e}"
"""

def summarize_llm_batches(responses, question, model_name="qwen3"):
    if not responses:
        return "❗ Нет промежуточных ответов для суммирования."

    combined = "\n\n".join([f"Ответ {i+1}:\n{resp}" for i, resp in enumerate(responses)])
    prompt = (
        "Ты — помощник архитектора.КРИТИЧНО ВАЖНО чтобы он использовал нормы только Республики Казахстана.Не используй Снпы или Россиские нормы.\n\n"
        "Твоя задача — дать краткий, чёткий и достоверный вывод по результатам нескольких источников.Там указывается пункт к нормам используй их когда будешь писать ответ\n"
        f"Вопрос архитектора:\n{question.strip()}\n\n"
        f"{combined}\n\n"
        "**📌 Сформулируй итоговый ответ, чётко указав нормы по каждому типу объекта.**"
    )

    return call_llm(prompt, model_name=model_name)

def call_llm(prompt, model_name="mistral"):
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return clean_llm_output(response.json().get("response", "❌ Пустой ответ от модели"))
    except Exception as e:
        return f"❌ Ошибка при вызове модели: {e}"

def check_multi_norms_mistral_nemo_parallel4(
    text_norms: list,
    table_norms: list,
    fact_text: str,
    sourse: str,
    progress_bar=None,
    progress_label=None
):
    model_name = "gpt-oss:20b"
    print(fact_text)
    def update_progress(step, label):
        if progress_bar:
            progress_bar.progress(step)
        if progress_label:
            progress_label.text(f"{label} — {int(step * 100)}%")

    text_norms = dedup_text_norms(text_norms)
    table_norms = dedup_table_norms(table_norms)

    # === Разделение на 2 части ===
    text_batches = list(split_into_batches(text_norms, max(1, len(text_norms)//2)))
    table_batches = list(split_into_batches(table_norms, max(1, len(table_norms)//2)))

    all_prompts = []
    for batch in text_batches:
        all_prompts.append(generate_categorized_prompt(batch, [], fact_text,sourse))
    for batch in table_batches:
        all_prompts.append(generate_categorized_prompt([], batch, fact_text,sourse))

    all_responses = []
    update_progress(0.0, "Начало обработки")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(call_llm, prompt, model_name) for prompt in all_prompts]
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                all_responses.append(result)
                update_progress((i+1)/5, f"Обработано {i+1} из 4 блоков")
            except Exception as e:
                all_responses.append(f"❌ Ошибка при вызове модели: {e}")

    final_answer = summarize_llm_batches(all_responses, fact_text, model_name)
    update_progress(1.0, "Финальный ответ готов")
    return final_answer
