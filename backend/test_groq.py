
from app.core.config import settings
from app.services.llm_service import llm_service

print("Groq API key loaded:", bool(settings.GROQ_API_KEY), flush=True)
print("Groq model:", settings.GROQ_MODEL, flush=True)

try:
    answer = llm_service.generate_answer(
        question="Explain Retrieval-Augmented Generation in two sentences.",
        retrieved_chunks=[
            {
                "filename": "test_document.pdf",
                "page_number": 1,
                "text": (
                    "Retrieval-Augmented Generation (RAG) combines "
                    "information retrieval with generative AI. "
                    "It retrieves relevant external information and "
                    "provides it as context to a language model."
                ),
            }
        ],
    )

    print("\nGroq response:", flush=True)
    print(answer, flush=True)

except Exception as error:
    print("\nGroq test failed!", flush=True)
    print(type(error).__name__, flush=True)
    print(str(error), flush=True)
