from typing import Any

from openai import OpenAI

from forecast_forge.config import get_settings


class NemotronProvider:
    """Adapter for the NVIDIA Nemotron API using OpenAI compatibility."""

    def __init__(self):
        settings = get_settings()
        if not settings.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is missing from environment.")

        self.client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
        self.model = settings.nvidia_model

    def generate_chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> Any:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,  # Low temp for scientific precision
            "top_p": 1,
            "max_tokens": 1024,
            "stream": False,
        }

        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message
