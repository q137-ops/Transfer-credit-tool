import httpx


class GoogleSearchProvider:
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        results = []
        remaining = max(1, min(max_results, 20))
        start = 1

        async with httpx.AsyncClient(timeout=25.0) as client:
            while remaining > 0:
                page_size = min(remaining, 10)
                resp = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.api_key,
                        "cx": self.cx,
                        "q": query,
                        "num": page_size,
                        "start": start,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })

                remaining -= len(items)
                start += len(items)

                if len(items) < page_size:
                    break

        return results
