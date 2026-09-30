import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google import genai
from config import Config

async def list_models():
    client = genai.Client(api_key=Config.llm.google_api_key)
    print("Available embedding models:")
    try:
        response = client.models.list_models()
        # This is a paginated list or iterable in some SDK versions
        for m in response:
            if "embed" in m.name.lower():
                print(m.name, m.supported_actions)
    except Exception as e:
        print("Error listing models:", e)

if __name__ == "__main__":
    asyncio.run(list_models())
