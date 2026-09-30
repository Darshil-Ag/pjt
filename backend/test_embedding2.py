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
        for model_name in ["text-embedding-004", "embedding-001", "models/embedding-001"]:
            print(f"\nTrying {model_name}...")
            try:
                response = await client.aio.models.embed_content(
                    model=model_name,
                    contents=["This is a test pitch."],
                )
                print("Success! Dimensions:", len(response.embeddings[0].values))
            except Exception as e:
                print("Error:", e)
    except Exception as e:
        print("Client Error:", e)

if __name__ == "__main__":
    asyncio.run(test_embed())
