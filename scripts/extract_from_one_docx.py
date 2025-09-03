from docx import Document
import re
import json
from pathlib import Path

# === Указание пути к загруженному файлу
INPUT_FILE = Path("./docs/Решение внеочередной XXVI сессии маслихата города Алматы VIII созыва от 25 декабря 2024 года № 194 Об у.docx")
OUTPUT_FILE = Path("./docs/new_norms_general_parser7.json")

# === Регулярка для поиска ID (например: "1", "4.1", "5.3.2.1")
NORM_PATTERN = re.compile(r'^\d+(\.\d+)*')

def extract_general_norms(file_path):
    doc = Document(file_path)
    blocks = []
    source = file_path.stem

    buffer = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Новый пункт начинается с ID
        match = NORM_PATTERN.match(text)
        if match:
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
        buffer.append(text)

    if buffer:
        blocks.append(" ".join(buffer))

    norms = []
    for block in blocks:
        match = NORM_PATTERN.match(block)
        if match:
            norm_id = match.group()
            norms.append({
                "id": norm_id,
                "text": block,
                "source": source,
                "full_id": f"{source}:{norm_id}"
            })

    return norms

# === Запуск
norms = extract_general_norms(INPUT_FILE)
print(f"✅ Извлечено {len(norms)} норм.")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(norms, f, ensure_ascii=False, indent=2)

print(f"💾 Сохранено в: {OUTPUT_FILE}")