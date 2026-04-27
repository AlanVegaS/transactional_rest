import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def get_summary(text: str) -> str:
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=f"Summarize the following text concisely:\n\n{text}",
    )
    return response.text
