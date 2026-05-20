import json
from openai import AsyncOpenAI


class OpenAIJsonClient:
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def json(self, payload: dict) -> dict:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON extraction engine for university online "
                        "credit course discovery. Return valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)
