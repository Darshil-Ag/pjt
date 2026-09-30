import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google import genai
from config import Config

async def test_embed():
    print("Testing Gemini embedding...")
    try:
        client = genai.Client(api_key=Config.llm.google_api_key)
        response = await client.aio.models.embed_content(
            model=Config.rag.embedding_model,
            contents=["This is a test pitch."],
        )
        print("Success! Dimensions:", len(response.embeddings[0].values))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_embed())
