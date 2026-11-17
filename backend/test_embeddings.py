
from app.rag.embeddings import embedding_service

sentences = [
    "Machine learning is a branch of artificial intelligence.",
    "ML is a field of AI that enables computers to learn.",
    "I enjoy playing football on weekends.",
]

embeddings = embedding_service.generate_embeddings(
    sentences
)

print("\nEmbedding Shape:")
print(embeddings.shape)

print("\nCosine Similarity Results:")

similarity_matrix = embeddings @ embeddings.T

for i in range(len(sentences)):

    for j in range(len(sentences)):

        print(
            f"Sentence {i + 1} vs Sentence {j + 1}: "
            f"{similarity_matrix[i][j]:.4f}"
        )

print("\nSentence 1:")
print(sentences[0])

print("\nSentence 2:")
print(sentences[1])

print("\nSentence 3:")
print(sentences[2])
