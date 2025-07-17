# model_loader.py
import torch
from sentence_transformers import SentenceTransformer
import streamlit as st

@st.cache_resource(show_spinner="🤖 Загружается модель...")  # безопасно кэшируем
def load_sentence_transformer_model(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    # Сперва загружаем на CPU — это важно
    model = SentenceTransformer(model_name, trust_remote_code=False)
    
    # После загрузки — перемещаем на устройство
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        model = model.cuda()
    else:
        model = model.cpu()
        
    return model
