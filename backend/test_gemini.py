
from google import genai
from app.core.config import settings
import time
import traceback

print("API key loaded:", bool(settings.GEMINI_API_KEY), flush=True)
print("Model:", settings.GEMINI_MODEL, flush=True)

try:
    print("\nCreating Gemini client...", flush=True)

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"timeout": 30000}
    )

    print("Client created.", flush=True)
    print("Sending request to Gemini...", flush=True)

    start_time = time.time()

    interaction = client.interactions.create(
        model=settings.GEMINI_MODEL,
        input="Explain RAG in two simple sentences.",
        timeout=40
    )

    print("\nResponse received!", flush=True)
    print("Time:", round(time.time() - start_time, 2), "seconds")
    print("Answer:", interaction.output_text, flush=True)

except Exception as error:
    print("\nGemini request failed!", flush=True)
    print("Error type:", type(error).__name__, flush=True)
    print("Error:", str(error), flush=True)
    traceback.print_exc()
