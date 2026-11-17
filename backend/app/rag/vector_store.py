import json
import logging
from pathlib import Path
from threading import RLock

import faiss
import numpy as np

from app.rag.embeddings import EMBEDDING_DIMENSION

logger = logging.getLogger("smart_document_assistant")

BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = BASE_DIR / "storage" / "vector_store"

INDEX_PATH = VECTOR_STORE_DIR / "faiss.index"
METADATA_PATH = VECTOR_STORE_DIR / "metadata.json"


class VectorStore:
    def __init__(self):
        self.index = None
        self.metadata = []
        self.lock = RLock()

        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.load_or_create()

    def create_index(self):
        """Create a normalized-vector inner-product index."""
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.metadata = []
        logger.info("Created a new FAISS index.")

    def load_or_create(self):
        """Load the existing FAISS index and its metadata."""
        with self.lock:
            if INDEX_PATH.exists() and METADATA_PATH.exists():
                try:
                    loaded_index = faiss.read_index(str(INDEX_PATH))

                    with METADATA_PATH.open("r", encoding="utf-8") as file:
                        loaded_metadata = json.load(file)

                    if loaded_index.d != EMBEDDING_DIMENSION:
                        raise ValueError("Stored FAISS dimension does not match.")

                    if loaded_index.ntotal != len(loaded_metadata):
                        raise ValueError("FAISS index and metadata counts differ.")

                    self.index = loaded_index
                    self.metadata = loaded_metadata

                    logger.info(
                        "Loaded FAISS index with %s vectors.",
                        self.index.ntotal
                    )
                    return

                except Exception:
                    logger.exception(
                        "Could not load the existing vector store."
                    )
                    raise

            self.create_index()
            self.save()

    def save(self):
        """Persist the FAISS index and metadata."""
        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

        temporary_index = INDEX_PATH.with_name("faiss.tmp")
        temporary_metadata = METADATA_PATH.with_name("metadata.tmp")

        faiss.write_index(self.index, str(temporary_index))

        with temporary_metadata.open("w", encoding="utf-8") as file:
            json.dump(self.metadata, file, ensure_ascii=False, indent=2)

        temporary_index.replace(INDEX_PATH)
        temporary_metadata.replace(METADATA_PATH)

        logger.info("Vector store saved successfully.")

    def add_embeddings(self, embeddings: np.ndarray, chunks: list):
        """Add new document embeddings without replacing existing documents."""
        if not chunks:
            return 0

        vectors = np.asarray(embeddings, dtype=np.float32)

        if vectors.ndim != 2:
            raise ValueError("Embeddings must be a 2D array.")

        if vectors.shape != (len(chunks), EMBEDDING_DIMENSION):
            raise ValueError("Embedding and chunk dimensions do not match.")

        if not np.isfinite(vectors).all():
            raise ValueError("Embeddings contain invalid numeric values.")

        norms = np.linalg.norm(vectors, axis=1)

        if not np.allclose(norms, 1.0, atol=1e-3):
            raise ValueError("Expected normalized embeddings.")

        document_ids = {chunk.get("document_id") for chunk in chunks}

        if None in document_ids or len(document_ids) != 1:
            raise ValueError("All chunks must belong to one valid document.")

        with self.lock:
            existing_document_ids = {
                item["document_id"] for item in self.metadata
            }

            if document_ids & existing_document_ids:
                raise ValueError(
                    "This document is already indexed."
                )

            old_index = faiss.deserialize_index(
                faiss.serialize_index(self.index)
            )
            old_metadata = self.metadata.copy()

            try:
                self.index.add(vectors)
                self.metadata.extend(chunks)
                self.save()

            except Exception:
                self.index = old_index
                self.metadata = old_metadata

                try:
                    self.save()
                except Exception:
                    logger.exception(
                        "Could not persist vector-store rollback."
                    )

                raise

        logger.info("Indexed %s document chunks.", len(chunks))
        return len(chunks)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: list[str] | None = None
    ):
        """
        Search all documents or restrict results to selected document IDs.

        Filtering is applied before top_k is selected, so chunks from
        other documents cannot occupy the selected document's result slots.
        """
        query_vector = np.asarray(
            query_embedding,
            dtype=np.float32
        ).reshape(1, -1)

        if query_vector.shape[1] != EMBEDDING_DIMENSION:
            raise ValueError("Query embedding has an invalid dimension.")

        if not np.isfinite(query_vector).all():
            raise ValueError("Query embedding contains invalid values.")

        norm = np.linalg.norm(query_vector)

        if not np.isclose(norm, 1.0, atol=1e-3):
            raise ValueError("Expected a normalized query embedding.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        allowed_ids = set(document_ids) if document_ids else None

        with self.lock:
            total_vectors = self.index.ntotal

            if total_vectors == 0:
                return []

            # Search all vectors when filtering, then apply document scope.
            search_count = (
                total_vectors
                if allowed_ids is not None
                else min(top_k, total_vectors)
            )

            scores, indices = self.index.search(
                query_vector,
                search_count
            )

            results = []

            for score, position in zip(scores[0], indices[0]):
                if position < 0:
                    continue

                chunk = self.metadata[int(position)]

                if (
                    allowed_ids is not None
                    and chunk.get("document_id") not in allowed_ids
                ):
                    continue

                result = chunk.copy()
                result["similarity_score"] = float(score)
                results.append(result)

                if len(results) >= top_k:
                    break

            return results

    def delete_document(self, document_id: str):
        """
        Delete a document's vectors and metadata while preserving
        all other documents in the FAISS index.
        """
        if not document_id:
            raise ValueError("A valid document ID is required.")

        with self.lock:
            matching_positions = [
                index
                for index, item in enumerate(self.metadata)
                if item.get("document_id") == document_id
            ]

            if not matching_positions:
                return {
                    "document_id": document_id,
                    "deleted_chunks": 0,
                    "remaining_vectors": self.index.ntotal,
                }

            # Extract all existing vectors before rebuilding the index.
            all_vectors = self.index.reconstruct_n(
                0,
                self.index.ntotal
            )

            matching_positions = set(matching_positions)

            # Identify vectors belonging to other documents.
            retained_positions = [
                index
                for index in range(self.index.ntotal)
                if index not in matching_positions
            ]

            retained_metadata = [
                item
                for index, item in enumerate(self.metadata)
                if index not in matching_positions
            ]

            retained_vectors = all_vectors[retained_positions]

            # Preserve the original state for rollback.
            old_index = faiss.deserialize_index(
                faiss.serialize_index(self.index)
            )
            old_metadata = self.metadata.copy()

            try:
                new_index = faiss.IndexFlatIP(
                    EMBEDDING_DIMENSION
                )

                if len(retained_vectors) > 0:
                    new_index.add(
                        np.asarray(
                            retained_vectors,
                            dtype=np.float32
                        )
                    )

                self.index = new_index
                self.metadata = retained_metadata

                self.save()

            except Exception:
                self.index = old_index
                self.metadata = old_metadata

                try:
                    self.save()
                except Exception:
                    logger.exception(
                        "Could not persist vector-store rollback."
                    )

                raise

            deleted_count = len(matching_positions)

            logger.info(
                "Deleted document %s and %s chunks.",
                document_id,
                deleted_count
            )

            return {
                "document_id": document_id,
                "deleted_chunks": deleted_count,
                "remaining_vectors": self.index.ntotal,
            }

    def get_total_vectors(self):
        with self.lock:
            return self.index.ntotal

    def get_document_ids(self):
        """Return IDs of all documents represented in the index."""
        with self.lock:
            return list({
                item.get("document_id")
                for item in self.metadata
                if item.get("document_id")
            })

    def get_documents(self):
        """Return a summary of every indexed document."""
        with self.lock:
            documents = {}

            for item in self.metadata:
                document_id = item.get("document_id")

                if not document_id:
                    continue

                if document_id not in documents:
                    documents[document_id] = {
                        "document_id": document_id,
                        "filename": item.get("filename", "Unknown document"),
                        "indexed_chunks": 0,
                    }

                documents[document_id]["indexed_chunks"] += 1

            return list(documents.values())


vector_store = VectorStore()