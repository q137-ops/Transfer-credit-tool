import re
from urllib.parse import urldefrag, urljoin

import httpx
from bs4 import BeautifulSoup

from .models import PageContent


class Crawler:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def fetch(self, url: str) -> PageContent:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 CourseDiscoveryBot/0.1 "
                "(educational research)"
            )
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        links = self._extract_links(soup, str(resp.url))

        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        text = soup.get_text(separator="\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = text.strip()

        return PageContent(
            url=str(resp.url),
            title=title,
            text=text[:50000],
            html=html,
            links=links,
        )

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
        links = []
        seen = set()

        for anchor in soup.find_all("a", href=True):
            label = anchor.get_text(" ", strip=True)
            href = anchor.get("href", "").strip()

            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue

            absolute_url = urldefrag(urljoin(base_url, href)).url

            if not absolute_url.startswith(("http://", "https://")):
                continue

            if absolute_url in seen:
                continue

            seen.add(absolute_url)
            links.append({
                "text": label[:200],
                "url": absolute_url,
            })

        return links
