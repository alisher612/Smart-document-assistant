import uuid
import zipfile
import logging
from pathlib import Path

import fitz
from docx import Document
from fastapi import UploadFile

from app.core.exceptions import AppException


logger = logging.getLogger("smart_document_assistant")

# Project storage directory
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"

# Maximum upload size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed document extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}


def create_upload_directory():
    """Create upload directory if it does not exist."""
    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def validate_extension(filename: str):
    """Validate uploaded file extension."""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise AppException(
            message="Unsupported file format. Upload PDF, DOCX or TXT.",
            status_code=400
        )

    return extension


def validate_file_content(file_path: Path, extension: str):
    """Validate actual file structure, not just its extension."""
    if extension == ".pdf":
        with open(file_path, "rb") as file:
            signature = file.read(5)

        if signature != b"%PDF-":
            raise AppException(
                message="Invalid PDF file.",
                status_code=400
            )

    elif extension == ".docx":
        if not zipfile.is_zipfile(file_path):
            raise AppException(
                message="Invalid DOCX file.",
                status_code=400
            )

    elif extension == ".txt":
        try:
            with open(file_path, "r", encoding="utf-8-sig") as file:
                file.read()

        except UnicodeDecodeError:
            raise AppException(
                message="TXT file must use UTF-8 encoding.",
                status_code=400
            )


async def save_uploaded_file(file: UploadFile):
    """Save uploaded document with a unique filename."""
    if not file.filename:
        raise AppException(
            message="Filename is required.",
            status_code=400
        )

    extension = validate_extension(file.filename)
    create_upload_directory()

    # Generate a unique server-side filename
    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}{extension}"
    file_path = UPLOAD_DIR / safe_filename
    file_size = 0

    try:
        with open(file_path, "wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise AppException(
                        message="Maximum upload size is 10 MB.",
                        status_code=413
                    )

                destination.write(chunk)

        if file_size == 0:
            raise AppException(
                message="Uploaded document is empty.",
                status_code=400
            )

        validate_file_content(file_path, extension)

        logger.info(
            "Document uploaded successfully: %s",
            safe_filename
        )

        return {
            "document_id": document_id,
            "original_filename": file.filename,
            "stored_filename": safe_filename,
            "file_path": file_path,
            "file_size": file_size,
            "extension": extension
        }

    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise

    finally:
        await file.close()


def extract_pdf_text(file_path: Path):
    """Extract text from PDF with page-level information."""
    pages = []

    try:
        with fitz.open(file_path) as pdf:
            if pdf.is_encrypted:
                raise AppException(
                    message="Password-protected PDFs are not supported.",
                    status_code=400
                )

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()

                pages.append({
                    "page_number": page_number,
                    "text": text
                })

    except AppException:
        raise

    except Exception:
        raise AppException(
            message="Unable to read this PDF document.",
            status_code=422
        )

    return pages


def extract_docx_text(file_path: Path):
    """Extract paragraphs and tables from DOCX."""
    try:
        document = Document(file_path)
        content = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                content.append(text)

        # Extract table contents too
        for table in document.tables:
            for row in table.rows:
                row_content = [
                    cell.text.strip()
                    for cell in row.cells
                ]
                content.append(" | ".join(row_content))

        text = "\n\n".join(content)

        return [{
            "page_number": None,
            "text": text
        }]

    except Exception:
        raise AppException(
            message="Unable to read this DOCX document.",
            status_code=422
        )


def extract_txt_text(file_path: Path):
    """Extract text from a TXT document."""
    try:
        with open(
            file_path,
            "r",
            encoding="utf-8-sig"
        ) as file:
            text = file.read()

        return [{
            "page_number": None,
            "text": text.strip()
        }]

    except UnicodeDecodeError:
        raise AppException(
            message="Unable to decode TXT document.",
            status_code=422
        )


def extract_document_text(document_data: dict):
    """Select the correct extraction method."""
    extension = document_data["extension"]
    file_path = document_data["file_path"]

    if extension == ".pdf":
        pages = extract_pdf_text(file_path)
    elif extension == ".docx":
        pages = extract_docx_text(file_path)
    elif extension == ".txt":
        pages = extract_txt_text(file_path)
    else:
        raise AppException(
            message="Unsupported document format.",
            status_code=400
        )

    extracted_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    if not extracted_text.strip():
        raise AppException(
            message=(
                "No extractable text found. "
                "This document may be scanned or image-based."
            ),
            status_code=422
        )

    word_count = len(extracted_text.split())

    logger.info(
        "Text extraction completed: %s words",
        word_count
    )

    return {
        "extracted_text": extracted_text,
        "pages": pages,
        "page_count": len(pages) if extension == ".pdf" else None,
        "word_count": word_count,
        "character_count": len(extracted_text)
    }