import pdfplumber
import json
from pathlib import Path

PDF_PATH = Path("docs/СП РК 3.02-101-2012_Здания жилые многоквартирные_ИЗМ. 01.03.2023.pdf")
OUTPUT_PATH = Path("extracted/class_norms.json")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

class_norms = []
start_reading = False
previous_indicator = None

with pdfplumber.open(PDF_PATH) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ""

        if not start_reading and "введение" in text.lower().replace(" ", ""):
            start_reading = True
            continue

        if not start_reading:
            continue

        tables = page.extract_tables()

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Определение заголовков
            header_row_idx = 1 if any(cell is None for cell in table[0]) else 0
            raw_headers = table[header_row_idx]
            raw_headers = [str(h).replace("\n", " ").strip() if h else "" for h in raw_headers]

            if header_row_idx == 1:
                first_row = table[0]
                headers = [
                    f"{str(first_row[i]).strip()} {raw_headers[i]}".strip()
                    if first_row[i] else raw_headers[i]
                    for i in range(len(raw_headers))
                ]
            else:
                headers = raw_headers

            if len(headers) < 2 or all(h == "" for h in headers[1:]):
                continue

            for row in table[header_row_idx + 1:]:
                if not row or len(row) < 2:
                    continue

                row = [str(cell).replace("\n", " ").strip() if cell else "" for cell in row]

                indicator = row[0]
                if not indicator:
                    indicator = previous_indicator
                else:
                    previous_indicator = indicator

                values = {}
                for i in range(1, min(len(headers), len(row))):
                    header = headers[i]
                    value = row[i]
                    if header and value:
                        values[header] = value

                if values:
                    class_norms.append({
                        "indicator": indicator,
                        "values": values
                    })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(class_norms, f, ensure_ascii=False, indent=2)

print(f"✅ Извлечено {len(class_norms)} строк табличных норм.")
print(f"💾 Сохранено в: {OUTPUT_PATH}")
