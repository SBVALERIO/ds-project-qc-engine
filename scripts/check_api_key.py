"""One-off: confirm the ANTHROPIC_API_KEY in .env is valid and billed,
without ever printing the key itself."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import anthropic

client = anthropic.Anthropic()
try:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=16,
        messages=[{"role": "user", "content": "reply with just: ok"}],
    )
    print("API key works. Response:", response.content[0].text)
except anthropic.AuthenticationError:
    print("AUTH ERROR: the key itself is invalid.")
except anthropic.PermissionDeniedError as e:
    print("PERMISSION ERROR:", e)
except anthropic.RateLimitError as e:
    print("RATE LIMIT / CREDIT ERROR (likely needs billing set up):", e)
except Exception as e:
    print(f"{type(e).__name__}:", e)
