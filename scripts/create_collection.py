from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

URL = "http://127.0.0.1:6333"
COL = "kb"

c = QdrantClient(url=URL, timeout=60, check_compatibility=False)

# На Qdrant 1.7.x recreate_collection надёжно работает
c.recreate_collection(
    collection_name=COL,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

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
for field, schema in [
    ("section",     PayloadSchemaType.KEYWORD),
    ("indicator",   PayloadSchemaType.KEYWORD),
]:
    try: c.create_payload_index(COL, field_name=field, field_schema=schema)
    except Exception: pass
print("Collection 'kb' ready at", URL)
