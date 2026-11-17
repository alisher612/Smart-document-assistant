
import uuid

from pathlib import Path

from fastapi import APIRouter, UploadFile, File
from starlette.concurrency import run_in_threadpool

from app.services.document_service import (
    save_uploaded_file,
    extract_document_text,
    UPLOAD_DIR,
)
from app.rag.chunking import split_document_into_chunks
from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.core.exceptions import AppException
from app.core.logging_config import logger

router = APIRouter()


@router.get("/")
async def list_documents():
    """Return all documents currently represented in FAISS."""
    documents = await run_in_threadpool(
        vector_store.get_documents
    )

    return {
        "success": True,
        "total_documents": len(documents),
        "documents": documents
    }


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload, extract, chunk, embed and index a document."""
    document_data = await save_uploaded_file(file)

    try:
        extraction_result = await run_in_threadpool(
            extract_document_text,
            document_data
        )

        chunks = split_document_into_chunks(
            pages=extraction_result["pages"],
            document_id=document_data["document_id"],
            filename=document_data["original_filename"]
        )

        if not chunks:
            raise AppException(
                "No valid text chunks were generated.",
                status_code=422
            )

        chunk_texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = await run_in_threadpool(
            embedding_service.generate_embeddings,
            chunk_texts
        )

        indexed_count = await run_in_threadpool(
            vector_store.add_embeddings,
            embeddings,
            chunks
        )

        logger.info(
            "Document %s processed and indexed.",
            document_data["document_id"]
        )

        return {
            "success": True,
            "message": "Document uploaded and indexed successfully.",
            "document": {
                "document_id": document_data["document_id"],
                "filename": document_data["original_filename"],
                "file_type": document_data["extension"],
                "file_size": document_data["file_size"],
                "page_count": extraction_result["page_count"],
                "word_count": extraction_result["word_count"],
                "character_count": extraction_result["character_count"]
            },
            "processing": {
                "total_chunks": len(chunks),
                "indexed_chunks": indexed_count,
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimension": int(embeddings.shape[1]),
                "total_vectors_in_store": vector_store.get_total_vectors()
            }
        }

    except AppException:
        raise

    except Exception:
        logger.exception(
            "Document processing or indexing failed."
        )

        raise AppException(
            "Document processing failed. Please check the backend logs.",
            status_code=500
        )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from:
    1. FAISS index
    2. FAISS metadata
    3. Local uploaded-file storage
    """

    # Validate UUID to prevent unsafe filesystem paths.
    try:
        document_id = str(uuid.UUID(document_id))
    except (ValueError, AttributeError):
        raise AppException(
            "Invalid document ID.",
            status_code=400
        )

    # Check whether this document exists in the vector store.
    documents = await run_in_threadpool(
        vector_store.get_documents
    )

    document = next(
        (
            item
            for item in documents
            if item["document_id"] == document_id
        ),
        None
    )

    if document is None:
        raise AppException(
            "Document not found.",
            status_code=404
        )

    # Find the actual uploaded file using its UUID-based filename.
    stored_file = None

    for extension in [".pdf", ".docx", ".txt"]:
        candidate = UPLOAD_DIR / f"{document_id}{extension}"

        if candidate.is_file():
            stored_file = candidate
            break

    # Move the uploaded file temporarily so it can be restored
    # if the FAISS deletion fails.
    temporary_file = None

    if stored_file is not None:
        temporary_file = stored_file.with_name(
            f".{stored_file.stem}.deleting{stored_file.suffix}"
        )

        try:
            stored_file.replace(temporary_file)

        except OSError:
            logger.exception(
                "Could not prepare uploaded file for deletion: %s",
                document_id
            )

            raise AppException(
                "Could not prepare the document file for deletion.",
                status_code=500
            )

    try:
        deletion_result = await run_in_threadpool(
            vector_store.delete_document,
            document_id
        )

    except Exception:
        # Restore the original uploaded file if index deletion fails.
        if (
            temporary_file is not None
            and temporary_file.exists()
        ):
            try:
                temporary_file.replace(stored_file)
            except OSError:
                logger.exception(
                    "Could not restore uploaded file after failed deletion."
                )

        logger.exception(
            "Failed to delete document %s from FAISS.",
            document_id
        )

        raise AppException(
            "Document deletion failed. Please check the backend logs.",
            status_code=500
        )

    # Remove the temporary file after successful FAISS deletion.
    file_deleted = True

    if temporary_file is not None:
        try:
            temporary_file.unlink()

        except OSError:
            file_deleted = False

            logger.exception(
                "Document was removed from FAISS, but its uploaded file "
                "could not be deleted: %s",
                document_id
            )

    logger.info(
        "Document %s deletion completed.",
        document_id
    )

    return {
        "success": True,
        "message": (
            "Document deleted successfully."
            if file_deleted
            else "Document removed from the search index, but its stored file could not be deleted."
        ),
        "document_id": document_id,
        "filename": document["filename"],
        "deleted_chunks": deletion_result["deleted_chunks"],
        "remaining_vectors": deletion_result["remaining_vectors"],
        "file_deleted": file_deleted
    }
