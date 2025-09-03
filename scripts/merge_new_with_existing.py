import json
from pathlib import Path

# Пути к файлам
EXISTING_TEXT_PATH = Path("extracted/norms_checklist_merged.json")
#NEW_TEXT_PATH = Path("docs/new_norms_general_parser6.json")
MERGED_TEXT_PATH = Path("extracted/norms_checklist_merged.json")

EXISTING_CLASS_PATH = Path("extracted/class_norms_merged.json")
#NEW_CLASS_PATH = Path("extracted/class_norms_auto2.json")
MERGED_CLASS_PATH = Path("extracted/class_norms_merged.json")


def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def merge_by_full_id(existing, new):
    existing_ids = {item["full_id"] for item in existing if "full_id" in item}
    unique_new = [item for item in new if item.get("full_id") not in existing_ids]
    return existing + unique_new


def merge_and_save(new_text,new_class):
    # Текстовые нормы
    existing_text = load_json(EXISTING_TEXT_PATH)
    new_text = load_json(new_text)
    merged_text = merge_by_full_id(existing_text, new_text)

    with open(MERGED_TEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_text, f, ensure_ascii=False, indent=2)
    print(f"✅ Текстовые нормы: добавлено {len(merged_text) - len(existing_text)} новых")

    # Табличные нормы
    existing_class = load_json(EXISTING_CLASS_PATH)
    new_class = load_json(new_class)
    merged_class = merge_by_full_id(existing_class, new_class)

    with open(MERGED_CLASS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_class, f, ensure_ascii=False, indent=2)
    print(f"✅ Табличные нормы: добавлено {len(merged_class) - len(existing_class)} новых")


if __name__ == "__main__":
    merge_and_save()
