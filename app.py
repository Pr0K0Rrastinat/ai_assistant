import streamlit as st
from pathlib import Path
import re
from norm_rag import NormRAG
from read_docx import check_multi_norms_combined_with_llama_parallel
from log_feedback import log_feedback
from scripts.search_class_norms import search as search_table_norms
from new_model_check import  check_multi_norms_mistral_nemo_parallel4 as check_multi_norms_mistral_nemo
import json
from scripts.extract_from_one_docx import extract_general_norms
from scripts.extract_class_norms import extract_from_docx_and_save
from scripts.convert_norms_to_checklist import convert_norms_to_checklist
from scripts.merge_new_with_existing import merge_and_save
from scripts.rebuild_faiss_index import rebuild_index_from_norms
from scripts.index_class_norms import build_class_norms_index
import tempfile
# === Настройки ===
BASE_DIR = Path(__file__).resolve().parent
RAG = NormRAG(base_dir=BASE_DIR, source_file="norms_checklist_merged.json")
available_domains = sorted({n.get("domain") for n in RAG.norms if n.get("domain")})

st.set_page_config(page_title="AI для Архитекторов", layout="wide")

# === Функция для преобразования ссылок в ответе ===
def linkify_norm_refs(text, current_sources):
    # Если передан не список — сделаем списком
    if not isinstance(current_sources, list):
        current_sources = [current_sources]

    def replace(match):
        norm_id = match.group(0)
        matched_norm = next(
            (
                norm for norm in RAG.norms
                if any(src.strip() == norm.get("source", "").strip() for src in current_sources)
                and norm.get("full_id", "").endswith(f":{norm_id}")
            ),
            None
        )

        if matched_norm:
            source = matched_norm.get("source", "").strip()
            tooltip = matched_norm.get("text", "").replace('"', "'").replace("\n", " ")
            return f'<a href="?norm_id={norm_id}" title="{tooltip}"><b>{source}:{norm_id}</b></a>'

        return norm_id  # если не нашли, возвращаем как есть

    return re.sub(r'\b\d{1,2}(?:\.\d{1,2}){1,4}\b', replace, text)

# === Обработка перехода по ссылке на конкретную норму ===
query_params = st.query_params
norm_id = query_params.get("norm_id")
if norm_id:
    norm = next((n for n in RAG.norms if n.get("full_id", "").endswith(norm_id)), None)
    st.title(f"📄 Норма {norm_id}")
    if norm:
        st.markdown(f"**Источник**: `{norm.get('source', 'неизвестен')}`")
        st.markdown(f"**Текст нормы:**\n\n{norm.get('text')}")
    else:
        st.error("❌ Норма не найдена.")
    st.markdown("[← Назад](./)")
    st.stop()


st.markdown("## 📥 Загрузка нового документа с нормами")

uploaded_file = st.file_uploader("Загрузите .docx с нормативами", type=["docx"])

if uploaded_file:
    temp_dir = Path("uploaded")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uploaded_file.name.replace(' ', '_')}"
    
    # Если файл существует — удалим
    if temp_path.exists():
        try:
            temp_path.unlink()
        except PermissionError:
            st.warning(f"⚠️ Не удалось удалить файл: {temp_path.name} — он занят другим процессом.")

    # Записываем
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"✅ Файл загружен: {temp_path.name}")

    if st.button("⚙️ Обработать документ"):
        with st.spinner("Извлекаем текстовые нормы..."):
            text_norms = extract_general_norms(temp_path)
            text_path = Path("extracted/temp_text_norms.json")
            with open(text_path, "w", encoding="utf-8") as f:
                json.dump(text_norms, f, ensure_ascii=False, indent=2)

        with st.spinner("Извлекаем табличные нормы..."):
            class_path = Path("extracted/temp_class_norms.json")
            class_norms = extract_from_docx_and_save(temp_path, class_path)

        with st.spinner("Генерируем чеклист..."):
            checklist_path = Path("extracted/temp_norms_checklist.json")
            convert_norms_to_checklist(text_norms, checklist_path)

        with st.spinner("Объединяем и обновляем индексы..."):
            merge_and_save(checklist_path, class_path)
            rebuild_index_from_norms(checklist_path)
            build_class_norms_index(class_path)

        st.success("🎉 Документ успешно обработан и проиндексирован!")

# === Основной интерфейс ===
st.title("📐 AI помощник по архитектурным нормам")

question = st.text_input("Введите вопрос архитектора (например, 'как проектировать лестницу?')")
available_sources = sorted(set(n.get("source") for n in RAG.norms if n.get("source")))

all_sources_raw = [n.get("source", "") for n in RAG.norms if n.get("source")]
selected_sources = st.multiselect("📄 Выберите документ (источник)",  ["— Все —"] +available_sources)
split_sources = [d.strip() for dom in all_sources_raw for d in dom.split(",")]
available_sources = sorted(set(split_sources))
source_filter = selected_sources if selected_sources != "— Все —" else None

applies_to = st.text_input("Тип помещения (опционально)", placeholder="лестница, коридор, кухня...")
all_domains_raw = [n.get("domain", "") for n in RAG.norms if n.get("domain")]
split_domains = [d.strip() for dom in all_domains_raw for d in dom.split(",")]
available_domains = sorted(set(split_domains))

# Выбор нескольких доменов
selected_domains = st.multiselect("Выберите одну или несколько сфер", available_domains)
domains = selected_domains if selected_domains else None

if st.button("🔍 Получить ответ"):
    st.session_state["feedback_logged"] = False

    if not question.strip():
        st.warning("Введите вопрос.")
    else:
        with st.spinner("🔎 Идёт поиск по нормативам..."):
            text_norms = RAG.query(question, top_k=64, applies_to=applies_to, domain=domains,source=source_filter)
            table_norms = search_table_norms(question, top_k=30)  # табличные нормы

        if not text_norms and not table_norms:
            st.error("❌ Ничего не найдено ни в текстовых, ни в табличных нормативах.")
        else:
            progress_label = st.empty()
            progress_bar = st.progress(0.0)
            progress_label.text("🚀 Генерация ответа...")

            answer = check_multi_norms_mistral_nemo(
                text_norms=text_norms,
                table_norms=table_norms,
                fact_text=question,
                sourse=source_filter,
                progress_bar=progress_bar,
                progress_label=progress_label
            )

            progress_bar.empty()
            
    
            st.session_state["last_question"] = question
            st.session_state["last_answer"] = answer
            st.session_state["last_text_norms"] = text_norms
            st.session_state["last_table_norms"] = table_norms


# === Отображение ответа, если он есть ===
if "last_answer" in st.session_state and st.session_state["last_answer"]:
    answer = st.session_state["last_answer"]
    text_norms = st.session_state.get("last_text_norms", [])
    final_response = answer
    if "**📌 Финальный ответ:**" in final_response:
        final_response = final_response.split("**📌 Финальный ответ:**", 1)[-1].strip()
    st.success("✅ Ответ:")
    st.markdown(linkify_norm_refs(final_response,source_filter), unsafe_allow_html=True)

    with st.expander("📄 Использованные нормы"):
        text_norms = st.session_state.get("last_text_norms", [])
        table_norms = st.session_state.get("last_table_norms", [])

        if text_norms:
            st.markdown("### 📘 Текстовые нормы:")
            for norm in text_norms:
                norm_id = norm.get("full_id", "")
                norm_text = norm.get("text", "")
                safe_text = norm_text.replace('"', "'").replace("\n", " ")
                st.markdown(f"""
                <div title="{safe_text}">
                    🔹 <a href="?norm_id={norm_id}" target="_self"><b>{norm_id}</b></a> — {norm_text}
                </div>
                """, unsafe_allow_html=True)

        if table_norms:
            st.markdown("### 📊 Табличные нормы:")
            for norm in table_norms:
                indicator = norm.get("indicator", "—")
                st.markdown(f"**◾ {indicator}**")
                values = norm.get("values", {})
                for cls, val in values.items():
                    st.markdown(f"- {cls}: {val}")


    st.markdown("🤔 Насколько полезен ответ?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Полезно", key="good_btn"):
            if not st.session_state.get("feedback_logged"):
                question = st.session_state.get("last_question", "")
                norm_ids = [n.get("id") for n in text_norms if n.get("id")]
                log_feedback(question, answer, norm_ids, 1)
                st.session_state["feedback_logged"] = True
                st.success("Спасибо за вашу оценку!")

    with col2:
        if st.button("👎 Неточно", key="bad_btn"):
            if not st.session_state.get("feedback_logged"):
                question = st.session_state.get("last_question", "")
                norm_ids = [n.get("id") for n in text_norms if n.get("id")]
                log_feedback(question, answer, norm_ids, 0)
                st.session_state["feedback_logged"] = True
                st.warning("Спасибо! Мы используем это для обучения.")
