
import re
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = logging.getLogger("smart_document_assistant")


# Chunking configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def clean_text(text: str) -> str:
    """
    Clean extracted document text while preserving
    meaningful paragraph boundaries.
    """

    if not text:
        return ""

    # Normalize Windows and Mac line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")

    # Remove null characters
    text = text.replace("\x00", "")

    # Normalize excessive spaces and tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces around line breaks
    text = re.sub(r" *\n *", "\n", text)

    # Reduce excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def create_text_splitter():
    """
    Configure the recursive character text splitter.
    """

    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            ""
        ],
        keep_separator=True
    )


def split_document_into_chunks(
    pages: list,
    document_id: str,
    filename: str
) -> list:
    """
    Split extracted document pages into chunks.

    Each chunk retains its document ID, original
    filename, page number and chunk index.
    """

    splitter = create_text_splitter()

    chunks = []

    chunk_index = 0

    for page in pages:

        original_text = page.get("text", "")

        cleaned_text = clean_text(original_text)

        if not cleaned_text:
            continue

        page_number = page.get("page_number")

        page_chunks = splitter.split_text(cleaned_text)

        for chunk_text in page_chunks:

            if not chunk_text.strip():
                continue

            chunk_index += 1

            chunks.append({

                "chunk_id": f"{document_id}_chunk_{chunk_index}",

                "document_id": document_id,

                "filename": filename,

                "page_number": page_number,

                "chunk_index": chunk_index,

                "text": chunk_text.strip(),

                "character_count": len(chunk_text.strip())

            })

    logger.info(
        "Created %s chunks for document %s",
        len(chunks),
        document_id
    )

    return chunks
