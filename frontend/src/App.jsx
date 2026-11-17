import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Bot,
  Check,
  CheckCircle2,
  File,
  FileText,
  LoaderCircle,
  Menu,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Trash2,
  UploadCloud,
  User,
  X,
} from "lucide-react";
import api from "./lib/api";
import "./App.css";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];

function getErrorMessage(error, fallback) {
  return (
    error.response?.data?.message ||
    error.response?.data?.detail ||
    error.message ||
    fallback
  );
}

function App() {
  const [serverStatus, setServerStatus] = useState("checking");
  const [documents, setDocuments] = useState([]);
  const [retrievalMode, setRetrievalMode] = useState("all");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [deletingDocumentId, setDeletingDocumentId] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I'm your Smart Document Assistant. Upload a document, then ask me questions about its contents. I'll provide answers grounded in your documents and show the sources I used.",
      sources: [],
    },
  ]);

  const [selectedFile, setSelectedFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    let active = true;

    const checkBackend = async () => {
      try {
        await api.get("/health");

        const response = await api.get("/documents/");
        const savedDocuments = (response.data.documents || []).map(
          (document) => ({
            ...document,
            processing: {
              indexed_chunks: document.indexed_chunks ?? 0,
            },
          })
        );

        if (active) {
          setDocuments(savedDocuments);
          setServerStatus("connected");
        }
      } catch (err) {
        console.error("Backend initialization failed:", err);
        if (active) setServerStatus("disconnected");
      }
    };

    checkBackend();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  const validateFile = (file) => {
    if (!file) return false;

    const extension = file.name
      .slice(file.name.lastIndexOf("."))
      .toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setError("Only PDF, DOCX, and TXT files are supported.");
      return false;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("The maximum document size is 10 MB.");
      return false;
    }

    if (file.size === 0) {
      setError("The selected document is empty.");
      return false;
    }

    setError("");
    setUploadMessage("");
    setSelectedFile(file);
    return true;
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    validateFile(file);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();

    const file = event.dataTransfer.files?.[0];
    validateFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setError("");
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await api.post("/documents/upload", formData);

      const uploadedDocument = {
        ...response.data.document,
        processing: response.data.processing,
        uploadedAt: new Date().toISOString(),
      };

      setDocuments((previous) => {
        const alreadyExists = previous.some(
          (item) => item.document_id === uploadedDocument.document_id
        );

        return alreadyExists
          ? previous
          : [uploadedDocument, ...previous];
      });

      setUploadMessage(
        `${uploadedDocument.filename} was uploaded and indexed successfully.`
      );

      setSelectedFile(null);

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Your document "${uploadedDocument.filename}" is ready. I indexed ${response.data.processing.indexed_chunks} text chunks. You can now ask questions about your uploaded documents.`,
          sources: [],
        },
      ]);
    } catch (err) {
      setError(
        getErrorMessage(err, "Document upload failed. Please try again.")
      );
    } finally {
      setUploading(false);
    }
  };

  const toggleDocumentSelection = (documentId) => {
    setSelectedDocumentIds((previous) =>
      previous.includes(documentId)
        ? previous.filter((id) => id !== documentId)
        : [...previous, documentId]
    );
  };

  const selectAllDocuments = () => {
    setSelectedDocumentIds(
      documents.map((document) => document.document_id)
    );
  };

  const clearDocumentSelection = () => {
    setSelectedDocumentIds([]);
  };

  const handleDeleteDocument = async (document) => {
    if (!document?.document_id || deletingDocumentId) return;

    const confirmed = window.confirm(
      `Delete "${document.filename}"? This will permanently remove it from your document library and search index.`
    );

    if (!confirmed) return;

    setDeletingDocumentId(document.document_id);
    setError("");
    setUploadMessage("");

    try {
      await api.delete(
        `/documents/${encodeURIComponent(document.document_id)}`
      );

      setDocuments((previous) =>
        previous.filter(
          (item) => item.document_id !== document.document_id
        )
      );

      setSelectedDocumentIds((previous) =>
        previous.filter((id) => id !== document.document_id)
      );

      setUploadMessage(`"${document.filename}" was deleted successfully.`);

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `The document "${document.filename}" has been deleted from your document library and search index.`,
          sources: [],
        },
      ]);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          `Could not delete "${document.filename}". Please try again.`
        )
      );
    } finally {
      setDeletingDocumentId(null);
    }
  };

  const handleAsk = async (event) => {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || asking) return;

    if (documents.length === 0) {
      setError("Upload at least one document before asking a question.");
      return;
    }

    if (
      retrievalMode === "selected" &&
      selectedDocumentIds.length === 0
    ) {
      setError("Select at least one document for document-specific search.");
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
      sources: [],
    };

    setMessages((previous) => [...previous, userMessage]);
    setQuestion("");
    setError("");
    setAsking(true);

    try {
      const response = await api.post("/answers/", {
        question: trimmedQuestion,
        top_k: 5,
        document_ids:
          retrievalMode === "selected"
            ? selectedDocumentIds
            : null,
      });

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.data.answer,
          sources: response.data.sources || [],
          retrievedChunks: response.data.retrieved_chunks || 0,
        },
      ]);
    } catch (err) {
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: getErrorMessage(
            err,
            "I couldn't generate an answer. Please try again."
          ),
          sources: [],
          failed: true,
        },
      ]);
    } finally {
      setAsking(false);
      textareaRef.current?.focus();
    }
  };

  const startNewConversation = () => {
    setMessages([
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "New conversation started. Ask me anything about your uploaded documents.",
        sources: [],
      },
    ]);
    setError("");
    setSidebarOpen(false);
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="workspace">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-mark">
            <FileText size={21} strokeWidth={2.2} />
          </div>

          <div className="brand-copy">
            <strong>DocuMind</strong>
            <span>Smart Document Assistant</span>
          </div>

          <button
            className="icon-button sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={19} />
          </button>
        </div>

        <button
          className="new-chat-button"
          onClick={startNewConversation}
        >
          <Plus size={18} />
          New conversation
        </button>

        <div className="sidebar-section">
          <div className="sidebar-section-heading">
            <span>YOUR DOCUMENTS</span>
            <span className="document-count">{documents.length}</span>
          </div>

          {documents.length === 0 ? (
            <div className="sidebar-empty">
              <FileText size={22} />
              <p>No documents uploaded yet.</p>
              <span>Your documents will appear here.</span>
            </div>
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <div className="document-item" key={document.document_id}>
                  <div className="document-icon">
                    <File size={17} />
                  </div>

                  <div className="document-item-info">
                    <strong title={document.filename}>
                      {document.filename}
                    </strong>
                    <span>
                      {document.processing?.indexed_chunks ?? 0} chunks
                    </span>
                  </div>

                  <CheckCircle2
                    className="document-check"
                    size={16}
                  />

                  <button
                    type="button"
                    className="document-delete-button"
                    onClick={() => handleDeleteDocument(document)}
                    disabled={
                      deletingDocumentId !== null || uploading || asking
                    }
                    aria-label={`Delete ${document.filename}`}
                    title={`Delete ${document.filename}`}
                  >
                    {deletingDocumentId === document.document_id ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="sidebar-bottom">
          <div className={`connection-card ${serverStatus}`}>
            <span className="connection-dot" />
            <div>
              <strong>
                {serverStatus === "connected"
                  ? "System operational"
                  : serverStatus === "checking"
                    ? "Connecting to API"
                    : "API disconnected"}
              </strong>
              <span>
                {serverStatus === "connected"
                  ? "Backend connection active"
                  : serverStatus === "checking"
                    ? "Checking server status"
                    : "Check your backend server"}
              </span>
            </div>
          </div>

          <span className="sidebar-version">SMART DOCUMENT ASSISTANT · 1.0</span>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>

            <div>
              <span className="breadcrumb">WORKSPACE</span>
              <h1>Document Intelligence</h1>
            </div>
          </div>

          <div className="topbar-right">
            <div className="topbar-status">
              <span className={`status-indicator ${serverStatus}`} />
              {serverStatus === "connected"
                ? "Connected"
                : serverStatus === "checking"
                  ? "Connecting"
                  : "Offline"}
            </div>
          </div>
        </header>

        <div className="workspace-content">
          <section className="welcome-section">
            <div className="welcome-copy">
              <div className="eyebrow">
                <Sparkles size={14} />
                YOUR AI DOCUMENT WORKSPACE
              </div>

              <h2>
                Knowledge at your
                <span> fingertips.</span>
              </h2>

              <p>
                Upload your documents, explore their content, and get
                accurate answers backed by relevant source references.
              </p>
            </div>

            <div className="welcome-decoration" aria-hidden="true">
              <div className="decoration-card decoration-card-back">
                <FileText size={24} />
              </div>
              <div className="decoration-card decoration-card-front">
                <Sparkles size={25} />
              </div>
            </div>
          </section>

          <div className="workspace-grid">
            <section className="upload-panel">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">STEP 01</span>
                  <h3>Upload documents</h3>
                  <p>Add files to your knowledge workspace.</p>
                </div>

                <div className="panel-heading-icon">
                  <UploadCloud size={20} />
                </div>
              </div>

              <div
                className={`drop-zone ${selectedFile ? "has-file" : ""}`}
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileChange}
                  hidden
                />

                <div className="drop-icon">
                  {selectedFile ? (
                    <FileText size={25} />
                  ) : (
                    <UploadCloud size={25} />
                  )}
                </div>

                <strong>
                  {selectedFile
                    ? selectedFile.name
                    : "Drop your file here"}
                </strong>

                <span>
                  {selectedFile
                    ? formatFileSize(selectedFile.size)
                    : "or click to browse from your computer"}
                </span>

                <div className="file-formats">
                  <span>PDF</span>
                  <span>DOCX</span>
                  <span>TXT</span>
                  <span>MAX 10 MB</span>
                </div>
              </div>

              {selectedFile && (
                <div className="selected-file-actions">
                  <span>
                    <Check size={15} />
                    File selected
                  </span>

                  <button
                    className="text-button"
                    onClick={() => setSelectedFile(null)}
                  >
                    Remove
                  </button>
                </div>
              )}

              <button
                className="primary-button upload-action"
                onClick={handleUpload}
                disabled={
                  !selectedFile ||
                  uploading ||
                  serverStatus !== "connected"
                }
              >
                {uploading ? (
                  <>
                    <LoaderCircle className="spin" size={17} />
                    Processing document...
                  </>
                ) : (
                  <>
                    <UploadCloud size={17} />
                    Upload and index
                  </>
                )}
              </button>

              {uploadMessage && (
                <div className="inline-message success-message">
                  <CheckCircle2 size={16} />
                  <span>{uploadMessage}</span>
                </div>
              )}

              {error && (
                <div className="inline-message error-message">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                  <button
                    className="message-dismiss"
                    onClick={() => setError("")}
                    aria-label="Dismiss error"
                  >
                    <X size={15} />
                  </button>
                </div>
              )}

              <div className="upload-note">
                <AlertCircle size={14} />
                Your files are processed and indexed by the backend.
              </div>
            </section>

            <section className="chat-panel">
              <div className="panel-heading chat-heading">
                <div>
                  <span className="panel-kicker">STEP 02</span>
                  <h3>Ask your documents</h3>
                  <p>Get answers grounded in your uploaded content.</p>
                </div>

                <div className="chat-heading-icon">
                  <MessageSquare size={20} />
                </div>
              </div>

              <div className="retrieval-scope">
                <div className="retrieval-scope-heading">
                  <div>
                    <strong>Search scope</strong>
                    <span>Choose which documents the assistant can use.</span>
                  </div>
                  <span className="retrieval-scope-hint">
                    {retrievalMode === "all"
                      ? "Searching all documents"
                      : `${selectedDocumentIds.length} selected`}
                  </span>
                </div>

                <div className="retrieval-mode-buttons">
                  <button
                    type="button"
                    className={`retrieval-mode-button ${retrievalMode === "all" ? "active" : ""
                      }`}
                    onClick={() => {
                      setRetrievalMode("all");
                      setError("");
                    }}
                    disabled={documents.length === 0}
                  >
                    All documents
                  </button>
                  <button
                    type="button"
                    className={`retrieval-mode-button ${retrievalMode === "selected" ? "active" : ""
                      }`}
                    onClick={() => {
                      setRetrievalMode("selected");
                      setError("");
                    }}
                    disabled={documents.length === 0}
                  >
                    Selected documents
                  </button>
                </div>

                {retrievalMode === "selected" && (
                  <div className="retrieval-document-picker">
                    <div className="retrieval-selection-summary">
                      <span>
                        Select one or more documents to search.
                      </span>
                      <div>
                        <button
                          type="button"
                          onClick={selectAllDocuments}
                          disabled={
                            selectedDocumentIds.length === documents.length
                          }
                        >
                          Select all
                        </button>
                        <button
                          type="button"
                          onClick={clearDocumentSelection}
                          disabled={selectedDocumentIds.length === 0}
                        >
                          Clear
                        </button>
                      </div>
                    </div>

                    <div className="retrieval-document-options">
                      {documents.map((document) => (
                        <label
                          className="retrieval-document-option"
                          key={document.document_id}
                        >
                          <input
                            type="checkbox"
                            checked={selectedDocumentIds.includes(
                              document.document_id
                            )}
                            onChange={() =>
                              toggleDocumentSelection(document.document_id)
                            }
                          />
                          <span className="retrieval-document-name">
                            {document.filename}
                          </span>
                          <span className="retrieval-document-chunks">
                            {document.processing?.indexed_chunks ??
                              document.indexed_chunks ??
                              0}{" "}
                            chunks
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="chat-messages">
                {messages.map((message) => (
                  <article
                    className={`chat-message ${message.role} ${message.failed ? "message-failed" : ""
                      }`}
                    key={message.id}
                  >
                    <div className="message-avatar">
                      {message.role === "assistant" ? (
                        <Bot size={18} />
                      ) : (
                        <User size={18} />
                      )}
                    </div>

                    <div className="message-body">
                      <div className="message-author">
                        {message.role === "assistant"
                          ? "Assistant"
                          : "You"}
                      </div>

                      {message.role === "assistant" ? (
                        <div className="assistant-answer">
                          {message.content}
                        </div>
                      ) : (
                        <p>{message.content}</p>
                      )}

                      {message.sources?.length > 0 && (
                        <details className="sources-section">
                          <summary className="sources-summary">
                            <span className="sources-summary-title">
                              <FileText size={15} />
                              Sources used
                              <span className="sources-count">
                                {message.sources.length}
                              </span>
                            </span>
                            <span className="sources-toggle-label">
                              View references
                            </span>
                          </summary>

                          <div className="sources-list">
                            {message.sources.map((source, index) => (
                              <article
                                className="source-card"
                                key={source.chunk_id || `${source.filename || "source"}-${index}`}
                              >
                                <div className="source-card-top">
                                  <div className="source-document">
                                    <span className="source-index">
                                      SOURCE {String(index + 1).padStart(2, "0")}
                                    </span>
                                    <strong title={source.filename || "Uploaded document"}>
                                      {source.filename || "Uploaded document"}
                                    </strong>
                                  </div>
                                  <span className="source-page">
                                    {source.page_number != null
                                      ? `Page ${source.page_number}`
                                      : "Page not provided"}
                                  </span>
                                </div>

                                {source.text_preview && (
                                  <p className="source-preview">
                                    {source.text_preview}
                                  </p>
                                )}

                                {source.similarity_score != null && (
                                  <div className="source-card-footer">
                                    <span className="source-score-label">
                                      Similarity score
                                    </span>
                                    <span className="source-score">
                                      {(source.similarity_score * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                              </article>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </article>
                ))}

                {asking && (
                  <div className="chat-message assistant">
                    <div className="message-avatar">
                      <Bot size={18} />
                    </div>

                    <div className="message-body">
                      <div className="message-author">Assistant</div>
                      <div className="typing-indicator">
                        <span />
                        <span />
                        <span />
                        <small>Searching documents and generating answer</small>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <form className="chat-composer" onSubmit={handleAsk}>
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder={
                    documents.length
                      ? "Ask a question about your documents..."
                      : "Upload a document to start asking questions..."
                  }
                  rows={2}
                  maxLength={2000}
                  disabled={asking || documents.length === 0}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                />

                <div className="composer-footer">
                  <span>
                    {documents.length > 0
                      ? retrievalMode === "all"
                        ? `All ${documents.length} documents`
                        : `${selectedDocumentIds.length} of ${documents.length} selected`
                      : "No documents available"}
                    {" · "}
                    {question.length}/2000
                  </span>

                  <button
                    type="submit"
                    className="send-button"
                    disabled={
                      !question.trim() ||
                      asking ||
                      documents.length === 0 ||
                      (retrievalMode === "selected" &&
                        selectedDocumentIds.length === 0)
                    }
                    aria-label="Send question"
                  >
                    {asking ? (
                      <LoaderCircle className="spin" size={17} />
                    ) : (
                      <Send size={17} />
                    )}
                  </button>
                </div>
              </form>

              <div className="chat-disclaimer">
                <Sparkles size={13} />
                AI responses are generated from retrieved document content.
                Always verify important information against the source.
              </div>
            </section>
          </div>

          <footer className="workspace-footer">
            <span>SMART DOCUMENT ASSISTANT</span>
            <span>Powered by semantic search and AI</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
