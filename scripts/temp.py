from tkinter import Tk, filedialog
from pathlib import Path
import json

from extract_from_one_docx import extract_general_norms
from extract_class_norms import extract_from_docx_and_save
from convert_norms_to_checklist import convert_norms_to_checklist
from merge_new_with_existing import merge_and_save
from rebuild_faiss_index import rebuild_index_from_norms
from index_class_norms import build_class_norms_index

import tkinter as tk
from tkinter import filedialog

def pick_file():
    root = tk.Tk()
    root.update()  # Важно: заставляем окно обновиться
    root.attributes("-topmost", True)  # окно поверх всех
    file_path = filedialog.askopenfilename(
        title="Выберите .docx файл с нормами",
        filetypes=[("Word Documents", "*.docx")]
    )
    root.destroy()  # закрыть окно после выбора
    return file_path


def run_norm_pipeline_with_file_picker():
    # === Открыть диалог выбора файла
    file_path = pick_file()

    if not file_path:
        print("❌ Файл не выбран. Операция отменена.")
        return

    docx_file = Path(file_path)
    print(f"📂 Выбран файл: {docx_file.name}")

    # === Пути
    extracted_dir = Path("extracted")
    extracted_dir.mkdir(parents=True, exist_ok=True)

    text_path = extracted_dir / "temp_text_norms.json"
    class_path = extracted_dir / "temp_class_norms.json"
    checklist_path = extracted_dir / "temp_norms_checklist.json"

    # === Извлечение текстовых норм
    print("📘 Извлекаем текстовые нормы...")
    text_norms = extract_general_norms(docx_file)
    with open(text_path, "w", encoding="utf-8") as f:
        json.dump(text_norms, f, ensure_ascii=False, indent=2)
    print(f"✅ Текстовые нормы: {len(text_norms)}")

    # === Извлечение табличных норм
    print("📊 Извлекаем табличные нормы...")
    class_norms = extract_from_docx_and_save(docx_file, class_path)
    print(f"✅ Табличные нормы: {len(class_norms)}")

    # === Генерация чек-листа
    print("🧾 Генерация чеклиста...")
    convert_norms_to_checklist(text_norms, checklist_path)

    # === Объединение
    print("🔗 Объединяем нормы...")
    merge_and_save(checklist_path, class_path)

    # === Перестройка индексов
    print("🔄 Перестраиваем индексы...")
    rebuild_index_from_norms(checklist_path)
    build_class_norms_index(class_path)

    print("✅ Всё выполнено успешно!")

# Вызов:
run_norm_pipeline_with_file_picker()