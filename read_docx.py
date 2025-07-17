import requests
import time
import re
import json

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


def summarize_llm_batches(responses, question, model_name="qwen3"):
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


def clean_llm_output(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def check_multi_norms_combined_with_llama(
    text_norms: list,
    table_norms: list,
    fact_text: str,
    model_name="qwen3",
    progress_bar=None,
    progress_label=None
):
    if not text_norms and not table_norms:
        return "❗ Нормативы не переданы, проверка невозможна."

    text_norms = dedup_text_norms(text_norms)
    table_norms = dedup_table_norms(table_norms)

    # Сливаем в один список, батчи одинаково делим
    all_pairs = list(zip(text_norms, [None]*len(text_norms))) + list(zip([None]*len(table_norms), table_norms))
    batches = list(split_into_batches(all_pairs, 8))
    total = len(batches)

    print(f"📦 Обнаружено {len(all_pairs)} норм (текст + таблица). Разбивка на {total} батчей по 8 норм.\n")

    all_responses = []
    start_time = time.time()

    for i, batch in enumerate(batches, 1):
        print(f"🔄 Обработка батча {i}/{total}... ", end="", flush=True)

        # Разделяем обратно на текстовые и табличные в каждом батче
        batch_text_norms = [t for t, _ in batch if t]
        batch_table_norms = [t for _, t in batch if t]

        prompt = generate_combined_prompt(batch_text_norms, batch_table_norms, fact_text)

        try:
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            })
            response.raise_for_status()
            result = response.json().get("response", "❌ Пустой ответ от модели")
            result = clean_llm_output(result)
            all_responses.append(result.strip())
            
            print("✅ Готово")
        except requests.exceptions.RequestException as e:
            all_responses.append(f"❌ Ошибка при подключении: {str(e)}")
            print("❌ Ошибка")

        if progress_bar and progress_label:
            percent = int((i / total) * 100)
            progress_bar.progress(i / total)
            progress_label.text(f"⌛ Выполнено: {percent}%")
    if progress_label:
        progress_label.text("✅ Генерация завершена")

    elapsed = time.time() - start_time
    print(f"\n🏁 Все батчи обработаны за {round(elapsed, 2)} сек.\n")
    print(f"Вопрос от архитектора {fact_text}")
    if all_responses:
        return clean_llm_output(summarize_llm_batches(all_responses, fact_text, model_name=model_name))
    else:
        return "❗ Нет ответов для генерации."


