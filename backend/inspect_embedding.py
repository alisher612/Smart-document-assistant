
from app.rag.embeddings import embedding_service

text = "Retrieval augmented generation combines search with language models."

vector = embedding_service.generate_single_embedding(text)

print("Original Text:")
print(text)

print("\nVector Shape:")
print(vector.shape)

print("\nFirst 10 Vector Values:")
print(vector[:10])

print("\nVector Type:")
print(vector.dtype)

print("\nVector Magnitude:")
print(round(float((vector @ vector) ** 0.5), 4))
