import re
import json
from pathlib import Path
from docx import Document

INPUT_FILE = Path("docs/СН РК 3.02-01-2023 Здания жилые многоквартирные.docx")  # ← заменишь на нужный
OUTPUT_FILE = Path("extracted/norms.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

NORM_PATTERN = re.compile(r'^\d+(?:\.\d+){1,4}')

def extract_from_docx(file_path):
    doc = Document(file_path)
    blocks = []
    current = None

    def save():
        nonlocal current
        if current:
            blocks.append(current)
            current = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        match = NORM_PATTERN.match(text)
        if match:
            save()
            current = {"id": match.group(), "text": text}
        elif current:
            current["text"] += " " + text

    save()
    return blocks

norms = extract_from_docx(INPUT_FILE)
print(f"✅ Извлечено {len(norms)} норм.")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(norms, f, ensure_ascii=False, indent=2)
print(f"💾 Сохранено в: {OUTPUT_FILE}")
