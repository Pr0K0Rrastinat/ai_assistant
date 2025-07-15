import requests
import time

def dedup_norms(norms):
    seen = set()
    deduped = []
    for norm in norms:
        text = norm.get("text", "")
        if text not in seen:
            deduped.append(norm)
            seen.add(text)
    return deduped

def split_into_batches(norms, batch_size):
    for i in range(0, len(norms), batch_size):
        yield norms[i:i + batch_size]

def generate_multi_norm_prompt(norms, fact_text):
    norms_text = "\n\n".join([f"- {n.get('text', '')}" for n in norms])
    prompt = (
        f"Вопрос архитектора:\n{fact_text.strip()}\n\n"
        f"Следующие нормы могут относиться к вопросу:\n{norms_text}\n\n"
        "На основе этих норм, дай краткий, полезный и понятный ответ архитектору на русском языке."
    )
    return prompt

import re

def clean_llm_output(text):
    # Убираем блоки размышлений в теге <think>...</think>
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def check_multi_norm_with_llama(norms, fact_text, model_name="qwen3"):
    if not norms:
        return "❗ Нормативы не переданы, проверка невозможна."

    norms = dedup_norms(norms)
    all_responses = []
    batches = list(split_into_batches(norms, 8))

    total = len(batches)
    print(f"📦 Обнаружено {len(norms)} норм. Разбивка на {total} батчей по 8 норм:\n")

    start_time = time.time()

    for i, batch in enumerate(batches, start=1):
        print(f"🔄 Обработка батча {i}/{total}... ", end="", flush=True)
        prompt = generate_multi_norm_prompt(batch, fact_text)

        try:
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            })
            response.raise_for_status()
            data = response.json()
            result = data.get("response", "❌ Пустой ответ от модели")
            all_responses.append(result.strip())
            print("✅ Готово")
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ Ошибка при подключении к LLaMA (батч {i}): {str(e)}"
            all_responses.append(error_msg)
            print("❌ Ошибка")

        time.sleep(1.5)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\n🏁 Все батчи обработаны за {round(elapsed, 2)} сек.\n")

    return clean_llm_output("\n\n".join(all_responses))
