# DocuMind — Smart Document Assistant

An AI-powered document question-answering system that allows users to upload documents, search their contents using semantic similarity, and receive context-aware answers with source references.

DocuMind uses **Retrieval-Augmented Generation (RAG)** to retrieve relevant information from uploaded documents before generating answers with a Large Language Model (LLM).

---

## Overview

Working with large documents can make finding specific information time-consuming. DocuMind addresses this problem by allowing users to upload documents and ask questions in natural language.

Instead of manually searching through pages, users can interact with their documents through an AI-powered question-answering interface.

The application extracts document content, divides it into smaller chunks, generates vector embeddings, stores them in FAISS, and retrieves relevant information when a question is submitted.

## Key Features

- **Multiple Document Upload:** Upload PDF, DOCX, and TXT files.
- **Document Text Extraction:** Extract text and available page information from uploaded documents.
- **Text Chunking:** Divide extracted content into smaller, manageable text segments.
- **Semantic Embeddings:** Convert document chunks and user questions into vector representations.
- **FAISS Vector Search:** Retrieve relevant document content using semantic similarity.
- **AI-Powered Answers:** Generate context-aware responses using the Groq API.
- **Source References:** Display source filenames, page information, text previews, and similarity scores.
- **Multiple Document Retrieval:** Search across all indexed documents or restrict retrieval to selected documents.
- **Document Management:** View indexed documents and delete documents from the application.
- **Persistent Vector Storage:** Store FAISS index data and associated metadata locally.
- **Interactive Web Interface:** Use a React-based interface to upload documents and ask questions.

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript |
| UI & Icons | CSS, Lucide React |
| Backend | Python, FastAPI |
| API Communication | Axios |
| Document Processing | PyMuPDF, python-docx |
| Text Chunking | LangChain Text Splitters |
| Embedding Model | Sentence Transformers |
| Embedding Model Name | all-MiniLM-L6-v2 |
| Vector Database | FAISS |
| Numerical Processing | NumPy |
| LLM Integration | Groq API |
| LLM SDK | Groq Python SDK |
| Configuration | Pydantic Settings |

## System Architecture

DocuMind follows a Retrieval-Augmented Generation architecture.

### Document Processing Pipeline

1. The user uploads a PDF, DOCX, or TXT document.
2. FastAPI validates the uploaded file.
3. The document service extracts its text.
4. The extracted text is cleaned and divided into chunks.
5. Sentence Transformers generates embeddings for each chunk.
6. FAISS stores the generated vectors.
7. Document metadata is maintained separately in JSON format.

### Question Answering Pipeline

1. The user submits a natural-language question.
2. The backend generates an embedding for the question.
3. FAISS searches for semantically relevant document chunks.
4. The retrieved chunks are passed to the Groq-powered LLM service.
5. The LLM generates an answer using the retrieved context.
6. The frontend displays the answer and its source references.

## Architecture Diagram

```text
                 USER
                   |
                   v
          REACT FRONTEND
                   |
                   v
             FASTAPI API
                   |
          +--------+--------+
          |                 |
          v                 v
    DOCUMENT SERVICE   ANSWER SERVICE
          |                 |
          v                 v
    TEXT EXTRACTION    QUESTION EMBEDDING
          |                 |
          v                 v
     TEXT CHUNKING      FAISS SEARCH
          |                 |
          v                 v
      EMBEDDINGS       RETRIEVED CHUNKS
          |                 |
          v                 v
     FAISS STORAGE     GROQ LLM SERVICE
                            |
                            v
                      GENERATED ANSWER
                            |
                            v
                     SOURCE REFERENCES
                            |
                            v
                      REACT FRONTEND
```

## Project Structure

```text
smart-document-assistant/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── search.py
│   │   │   │   └── answers.py
│   │   │   └── router.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   └── logging_config.py
│   │   │
│   │   ├── models/
│   │   │
│   │   ├── rag/
│   │   │   ├── chunking.py
│   │   │   ├── embeddings.py
│   │   │   └── vector_store.py
│   │   │
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   └── llm_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── storage/
│   │   ├── uploads/
│   │   └── vector_store/
│   │       ├── faiss.index
│   │       └── metadata.json
│   │
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── lib/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── .env
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.12
- Node.js and npm
- Git
- A Groq API key

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd smart-document-assistant
```

### 2. Configure the Backend

Open the backend directory:

```bash
cd backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file in the backend directory and configure:

```env
APP_NAME=Smart Document Assistant API
APP_VERSION=1.0.0
DEBUG=False
API_V1_PREFIX=/api/v1

FRONTEND_ORIGIN=http://localhost:5173
LOG_LEVEL=INFO

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b

MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=smart_document_assistant
```

Replace `your_groq_api_key` with your own Groq API key.

The current document retrieval and vector storage implementation uses FAISS and local files. Configure any additional environment values required by your actual project setup.

### 3. Start the Backend

Run from the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

### 4. Configure the Frontend

Open another terminal:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Configure the frontend `.env` file:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 5. Start the Frontend

```powershell
npm run dev
```

Open the application:

```text
http://localhost:5173
```

## Core RAG Components

### 1. Document Extraction

DocuMind supports three document formats:

- PDF — extracted using PyMuPDF.
- DOCX — extracted using python-docx.
- TXT — extracted using UTF-8 text decoding.

### 2. Text Chunking

Extracted content is divided into smaller chunks using the Recursive Character Text Splitter.

Current configuration:

- Chunk size: 800 characters
- Chunk overlap: 120 characters

Chunk metadata includes document ID, filename, page number, and chunk index.

### 3. Embedding Generation

The application uses:

`sentence-transformers/all-MiniLM-L6-v2`

The model converts text into numerical vector representations.

- Embedding dimensions: 384
- Normalized embeddings
- Local embedding generation

### 4. Vector Search

FAISS is used for efficient similarity search.

The application uses:

`faiss.IndexFlatIP(384)`

Because embeddings are normalized, inner-product similarity corresponds to cosine similarity.

### 5. LLM Answer Generation

The Groq API powers the answer-generation component.

Retrieved document chunks are included as context in the LLM prompt. The model is instructed to answer using the available document information rather than inventing unsupported details.

## API Endpoints

The following endpoints are part of the current backend API.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check backend health |
| POST | `/api/v1/documents/upload` | Upload and process a document |
| GET | `/api/v1/documents/` | Retrieve indexed documents |
| DELETE | `/api/v1/documents/{document_id}` | Delete a document |
| POST | `/api/v1/search/` | Perform semantic search |
| POST | `/api/v1/answers/` | Generate an AI-powered answer |

Refer to the FastAPI Swagger documentation for the exact request and response schemas.

## Limitations

- Scanned image-only PDFs are not supported because OCR is not currently implemented.
- Document uploads are limited to 10 MB.
- PDF page information is available through extraction; DOCX and TXT page numbers are not reliably available.
- Uploaded documents and FAISS data are stored locally in the current implementation.
- Answer quality depends on the relevance and coverage of retrieved document chunks.
- A valid Groq API key and an available configured model are required for answer generation.

## Future Scope

Potential future enhancements include:

- OCR support for scanned documents.
- Additional document formats.
- Improved retrieval strategies for large document collections.
- More advanced document analytics.
- Cloud-based document and vector storage.
- Authentication and multi-user document management.

## Author

**Ali Sher**

Computer Science Student | Full Stack Developer

Islamabad, Pakistan

- Portfolio: https://ali-sher-portfolio-dev.vercel.app/
- LinkedIn: https://www.linkedin.com/in/alisherdev
- GitHub: Add your GitHub profile URL

---

**DocuMind — Making document understanding faster through AI-powered retrieval and question answering.**
