import streamlit as st
from pathlib import Path
import re
from norm_rag import NormRAG
from read_docx import check_multi_norms_combined_with_llama
from log_feedback import log_feedback
from scripts.search_class_norms import search as search_table_norms

# === Настройки ===
BASE_DIR = Path(__file__).resolve().parent
RAG = NormRAG(base_dir=BASE_DIR, source_file="norms_checklist_v2.json")

st.set_page_config(page_title="AI для Архитекторов", layout="wide")

# === Функция для преобразования ссылок в ответе ===
def linkify_norm_refs(text):
    def replace(match):
        norm_id = match.group(0)
        url = f"?norm_id={norm_id}"
        norm = next((n for n in RAG.norms if n.get("id") == norm_id), None)
        tooltip = norm.get("text", "").replace('"', "'").replace("\n", " ") if norm else ""
        return f'<a href="{url}" title="{tooltip}"><b>{norm_id}</b></a>'
    return re.sub(r'\b\d{1,2}(?:\.\d{1,2}){1,4}\b', replace, text)

# === Обработка перехода по ссылке на конкретную норму ===
query_params = st.query_params
norm_id = query_params.get("norm_id")
if norm_id:
    norm = next((n for n in RAG.norms if n.get("id") == norm_id), None)
    st.title(f"📄 Норма {norm_id}")
    if norm:
        st.markdown(f"**Источник**: `{norm.get('source', 'неизвестен')}`")
        st.markdown(f"**Текст нормы:**\n\n{norm.get('text')}")
    else:
        st.error("❌ Норма не найдена.")
    st.markdown("[← Назад](./)")
    st.stop()

# === Основной интерфейс ===
st.title("📐 AI помощник по архитектурным нормам")

question = st.text_input("Введите вопрос архитектора (например, 'как проектировать лестницу?')")
applies_to = st.text_input("Тип помещения (опционально)", placeholder="лестница, коридор, кухня...")

if st.button("🔍 Получить ответ"):
    st.session_state["feedback_logged"] = False

    if not question.strip():
        st.warning("Введите вопрос.")
    else:
        with st.spinner("🔎 Идёт поиск по нормативам..."):
            text_norms = RAG.query(question, top_k=20, applies_to=applies_to)
            table_norms = search_table_norms(question, top_k=10)  # табличные нормы

        if not text_norms and not table_norms:
            st.error("❌ Ничего не найдено ни в текстовых, ни в табличных нормативах.")
        else:
            progress_label = st.empty()
            progress_bar = st.progress(0.0)
            progress_label.text("🚀 Генерация ответа...")

            answer = check_multi_norms_combined_with_llama(
                text_norms=text_norms,
                table_norms=table_norms,
                fact_text=question,
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
    norms = st.session_state.get("last_norms", [])
    final_response = answer
    if "**📌 Финальный ответ:**" in final_response:
        final_response = final_response.split("**📌 Финальный ответ:**", 1)[-1].strip()
    st.success("✅ Ответ:")
    st.markdown(linkify_norm_refs(final_response), unsafe_allow_html=True)

    with st.expander("📄 Использованные нормы"):
        text_norms = st.session_state.get("last_text_norms", [])
        table_norms = st.session_state.get("last_table_norms", [])

        if text_norms:
            st.markdown("### 📘 Текстовые нормы:")
            for norm in text_norms:
                norm_id = norm.get("id", "")
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
                norm_ids = [n.get("id") for n in norms if n.get("id")]
                log_feedback(question, answer, norm_ids, 1)
                st.session_state["feedback_logged"] = True
                st.success("Спасибо за вашу оценку!")

    with col2:
        if st.button("👎 Неточно", key="bad_btn"):
            if not st.session_state.get("feedback_logged"):
                question = st.session_state.get("last_question", "")
                norm_ids = [n.get("id") for n in norms if n.get("id")]
                log_feedback(question, answer, norm_ids, 0)
                st.session_state["feedback_logged"] = True
                st.warning("Спасибо! Мы используем это для обучения.")
