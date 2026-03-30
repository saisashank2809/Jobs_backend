import os
import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def test_key():
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("API Key is VALID")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"API Key is INVALID: {e}")

if __name__ == "__main__":
    asyncio.run(test_key())
