import os

from .google_provider import GoogleSearchProvider
from .tavily_provider import TavilySearchProvider


def build_search_provider():
    provider_name = os.getenv("SEARCH_PROVIDER", "google").strip().lower()

    if provider_name == "google":
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        cx = os.getenv("GOOGLE_SEARCH_CX")

        if not api_key:
            raise RuntimeError("Missing GOOGLE_SEARCH_API_KEY environment variable.")

        if not cx:
            raise RuntimeError("Missing GOOGLE_SEARCH_CX environment variable.")

        return GoogleSearchProvider(api_key=api_key, cx=cx)

    if provider_name == "tavily":
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise RuntimeError("Missing TAVILY_API_KEY environment variable.")

        return TavilySearchProvider(api_key=api_key)

    raise RuntimeError(
        "Unsupported SEARCH_PROVIDER. Use 'google' or 'tavily'."
    )
