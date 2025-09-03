import requests
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
def dedup_text_norms(norms):
    seen = set()
    deduped = []
    for norm in norms:
        text = norm.get("text", "")
        if text and text not in seen:
            deduped.append(norm)
            seen.add(text)
    return deduped

def dedup_table_norms(norms):
    seen = set()
    deduped = []
    for norm in norms:
        indicator = norm.get("indicator", "")
        values_str = json.dumps(norm.get("values", {}), ensure_ascii=False)
        key = f"{indicator}:{values_str}"
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
    return f"- {text}"

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
        "\n\n".join(parts) +
        "\n\nНа основе этих нормативов, дай краткий, полезный и понятный ответ архитектору на русском языке. "
    )

    return prompt


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
        f"Ты — помощник архитектора. Отвечай кратко, строго по нормам.\n\n"
        f"Вопрос:\n{question.strip()}\n\n"
        f"{combined}\n\n"
        "**📌 Финальный ответ:**"
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

def check_multi_norms_combined_with_llama_parallel(
    text_norms: list,
    table_norms: list,
    fact_text: str,
    model_name="mistral",
    max_workers=4,
    progress_bar=None,
    progress_label=None
):
    if not text_norms and not table_norms:
        return "❗ Нормативы не переданы, проверка невозможна."

    # === Удаляем дубликаты
    text_norms = dedup_text_norms(text_norms)
    table_norms = dedup_table_norms(table_norms)

    all_responses = []
    start_time = time.time()

    # === ТЕКСТОВЫЕ НОРМЫ ===
    def process_text_batch(batch):
        prompt = generate_combined_prompt(batch, [], fact_text)
        return call_llm(prompt, model_name=model_name)

    text_batches = list(split_into_batches(text_norms, 8))
    print(f"📝 Текстовых норм: {len(text_norms)}, батчей: {len(text_batches)}")
    table_batches = list(split_into_batches(table_norms, 8))
    print(f"📊 Табличных норм: {len(table_norms)}, батчей: {len(table_batches)}")
    total_batches = len(text_batches) + len(table_batches)
    progress_count = 0
    def update_progress(label=None):
        nonlocal progress_count
        progress_count += 1
        fraction = progress_count / total_batches
        if progress_bar:
            progress_bar.progress(fraction)
        if progress_label and label:
            percent = int(fraction * 100)
            progress_label.text(f"{label} — {percent}%")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_text_batch, batch): i for i, batch in enumerate(text_batches, 1)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                print("====")
                print(result)
                all_responses.append(result)
                update_progress()
                print(f"✅ Текстовый батч {idx} завершён.")
            except Exception as e:
                print(f"❌ Ошибка в текстовом батче {idx}: {e}")
                all_responses.append(f"❌ Ошибка в текстовом батче {idx}: {e}")


    # === ТАБЛИЧНЫЕ НОРМЫ ===
    def process_table_batch(batch):
        prompt = generate_combined_prompt([], batch, fact_text)
        return call_llm(prompt, model_name=model_name)


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_table_batch, batch): i for i, batch in enumerate(table_batches, 1)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                print("====")
                print(result)
                all_responses.append(result)
                print(f"✅ Табличный батч {idx} завершён.")
                update_progress()
            except Exception as e:
                print(f"❌ Ошибка в табличном батче {idx}: {e}")
                all_responses.append(f"❌ Ошибка в табличном батче {idx}: {e}")

    # === Финальное суммирование
    elapsed = time.time() - start_time
    print(f"\n🏁 Все батчи обработаны за {round(elapsed, 2)} сек.")
    print(f"Вопрос архитектора: {fact_text}")

    if all_responses:
        return clean_llm_output(summarize_llm_batches(all_responses, fact_text, model_name=model_name))
    else:
        return "❗ Нет ответов для генерации."