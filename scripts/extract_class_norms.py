import docx2pdf
import pdfplumber
import json
from pathlib import Path
import tempfile
import shutil
import pythoncom

"""def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path:
    pythoncom.CoInitialize()  # <---- Добавлено
    output_pdf = output_dir / (docx_path.stem + ".pdf")
    docx2pdf.convert(str(docx_path), str(output_pdf))
    pythoncom.CoUninitialize()  # <---- Желательно освободить
    return output_pdf"""


import subprocess
import sys

def convert_via_external(docx_path: Path, pdf_path: Path):
    subprocess.run(
        [sys.executable, "scripts/convert_docx_external.py", str(docx_path), str(pdf_path)],
        check=True
    )

def extract_class_norms_from_pdf(pdf_path: Path) -> list:
    """Парсинг табличных норм из PDF"""
    source = pdf_path.stem
    if "." in source.split()[0]:
        source = " ".join(source.split()[1:])

    norms = []
    previous_indicator = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

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
                        norms.append({
                            "indicator": indicator,
                            "values": values,
                            "source": source,
                            "full_id": f"{source}:{indicator}"
                        })

    return norms

def extract_from_docx_and_save(docx_path: Path, output_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        pdf_path = tmpdir / (docx_path.stem + ".pdf")
        convert_via_external(docx_path, pdf_path)

        class_norms = extract_class_norms_from_pdf(pdf_path)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(class_norms, f, ensure_ascii=False, indent=2)

        print(f"✅ Извлечено: {len(class_norms)} табличных норм")
        print(f"💾 Сохранено в: {output_path}")
    return class_norms
# === Пример использования ===
if __name__ == "__main__":
    docx_file = Path("docs/Решение внеочередной XXVI сессии маслихата города Алматы VIII созыва от 25 декабря 2024 года № 194 Об у.docx")
    output_file = Path("extracted/class_norms_auto3.json")
    extract_from_docx_and_save(docx_file, output_file)
