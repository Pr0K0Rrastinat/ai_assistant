import json
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("feedback.jsonl")

def log_feedback(question, answer, norm_ids, score: int):
    if not question or not answer or not norm_ids:
        print("⚠️ Пропущена запись: пустые поля")
        return

    record = {
        "question": question,
        "answer": answer,
        "norm_ids": norm_ids,
        "score": score,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"✅ Feedback сохранён: {record}")
