from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.core.exceptions import AppException

router = APIRouter()


class SearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )


@router.post("/")
async def search_documents(request: SearchRequest):
    if vector_store.get_total_vectors() == 0:
        raise AppException(
            "No documents have been indexed yet. Upload a document first.",
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

        results = await run_in_threadpool(
            vector_store.search,
            query_embedding,
            request.top_k,
            request.document_ids
        )

        return {
            "success": True,
            "question": request.question,
            "total_results": len(results),
            "results": results
        }

    except AppException:
        raise

    except Exception:
        raise AppException(
            "Semantic search failed. Please check the backend logs.",
            status_code=500
        )