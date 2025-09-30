# scripts/create_collection.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

URL = "http://127.0.0.1:6333"
COL = "kb"

# check_compatibility=False чтобы убрать ворнинг о версиях
c = QdrantClient(url=URL, timeout=60, check_compatibility=False)

# На 1.7.x используем recreate_collection — совместимо
c.recreate_collection(
    collection_name=COL,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Индексы для фильтров (если уже есть — просто проглотим ошибку)
for field, schema in [
    ("corpus",       PayloadSchemaType.KEYWORD),
    ("domain",       PayloadSchemaType.KEYWORD),
    ("applies_to",   PayloadSchemaType.KEYWORD),
    ("edition_date", PayloadSchemaType.KEYWORD),
    ("lang",         PayloadSchemaType.KEYWORD),
    ("is_recent",    PayloadSchemaType.BOOL),
]:
    try:
        c.create_payload_index(COL, field_name=field, field_schema=schema)
    except Exception:
        pass

print("Collection 'kb' ready at", URL)
