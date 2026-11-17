
import logging

import numpy as np

from sentence_transformers import SentenceTransformer


logger = logging.getLogger("smart_document_assistant")


# Embedding model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

EMBEDDING_DIMENSION = 384


class EmbeddingService:
    """
    Generate local semantic embeddings
    using Sentence Transformers.
    """

    def __init__(self):

        self.model = None

    def load_model(self):

        if self.model is None:

            logger.info(
                "Loading embedding model: %s",
                MODEL_NAME
            )

            self.model = SentenceTransformer(
                MODEL_NAME
            )

            logger.info(
                "Embedding model loaded successfully."
            )

        return self.model

    def generate_embeddings(
        self,
        texts: list[str]
    ) -> np.ndarray:

        if not texts:

            return np.empty(
                (0, EMBEDDING_DIMENSION),
                dtype=np.float32
            )

        model = self.load_model()

        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32
        )

        if embeddings.ndim != 2:
            raise ValueError(
                "Embedding output must be a 2D array."
            )

        if embeddings.shape[1] != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected {EMBEDDING_DIMENSION} dimensions, "
                f"received {embeddings.shape[1]}."
            )

        if not np.isfinite(embeddings).all():
            raise ValueError(
                "Embedding output contains invalid numerical values."
            )

        logger.info(
            "Generated embeddings for %s chunks.",
            len(texts)
        )

        return embeddings

    def generate_single_embedding(
        self,
        text: str
    ) -> np.ndarray:

        embeddings = self.generate_embeddings(
            [text]
        )

        return embeddings[0]


# Shared embedding service
embedding_service = EmbeddingService()
