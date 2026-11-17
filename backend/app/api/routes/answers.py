import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import AppException
from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.services.llm_service import llm_service

logger = logging.getLogger("smart_document_assistant")

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    document_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )


@router.post("/")
async def ask_question(request: AskRequest):
    """Retrieve document chunks and generate a grounded answer."""

    if vector_store.get_total_vectors() == 0:
        raise AppException(
            "No documents have been indexed. Upload a document first.",
            status_code=404
        )

    try:
        if request.document_ids:
            available_ids = set(vector_store.get_document_ids())
            unknown_ids = set(request.document_ids) - available_ids

            if unknown_ids:
                raise AppException(
                    "One or more selected documents are not indexed.",
                    status_code=404
                )

        query_embedding = await run_in_threadpool(
            embedding_service.generate_single_embedding,
            request.question
        )

        retrieved_chunks = await run_in_threadpool(
            vector_store.search,
            query_embedding,
            request.top_k,
            request.document_ids
        )

        if not retrieved_chunks:
            return {
                "success": True,
                "question": request.question,
                "answer": (
                    "I could not find relevant information in "
                    "the selected documents to answer this question."
                ),
                "sources": [],
                "retrieved_chunks": 0
            }

        answer = await run_in_threadpool(
            llm_service.generate_answer,
            request.question,
            retrieved_chunks
        )

        sources = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "filename": chunk.get("filename"),
                "page_number": chunk.get("page_number"),
                "similarity_score": chunk.get("similarity_score"),
                "text_preview": chunk.get("text", "")[:300]
            }
            for chunk in retrieved_chunks
        ]

        logger.info(
            "Answered question using %s retrieved chunks across %s documents.",
            len(retrieved_chunks),
            len({chunk.get("document_id") for chunk in retrieved_chunks})
        )

        return {
            "success": True,
            "question": request.question,
            "answer": answer,
            "retrieved_chunks": len(retrieved_chunks),
            "sources": sources
        }

    except AppException:
        raise

    except Exception:
        logger.exception("Question answering failed.")

        raise AppException(
            "Could not generate an answer. Please check the backend logs.",
            status_code=500
        )