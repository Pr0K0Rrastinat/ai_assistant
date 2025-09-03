from collections import defaultdict


def extract_object_category(norm: dict) -> str:
    source = norm.get("source", "").lower()

    if "жилые" in source or "многоквартирные" in source:
        return "Жилые здания"
    elif "дошкольные" in source or "доу" in source:
        return "Дошкольные учреждения"
    elif "общеобразовательные" in source or "школ" in source:
        return "Школы"
    elif "административные" in source or "бытовые" in source:
        return "Административные здания"
    elif "все здания" in norm.get("applies_to", []):
        return "Общие нормы"
    else:
        return "Прочие"


def group_norms_by_category(norms: list) -> dict:
    grouped = defaultdict(list)
    for norm in norms:
        category = extract_object_category(norm)
        grouped[category].append(norm)
    return grouped
