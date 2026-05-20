import re
from .models import PageContent, CourseFact
from .search_agent import SearchAgent
from .crawler import Crawler


PRICE_PATTERNS = [
    (re.compile(r"\$\s?(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)\s*\+\s*\$\s?(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)", re.I), "price_per_course"),
    (re.compile(r"\$\s?(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)\s*(?:/|per)?\s*credit", re.I), "price_per_credit"),
    (re.compile(r"\$\s?(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)\s*(?:per course|course fee)", re.I), "price_per_course"),
    (re.compile(r"(?:tuition|cost|fee)[^$]{0,80}\$\s?(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)", re.I), "price_candidate"),
]


class PriceResolver:
    def __init__(
        self,
        search_agent: SearchAgent,
        crawler: Crawler,
        llm_client=None,
    ):
        self.search_agent = search_agent
        self.crawler = crawler
        self.llm_client = llm_client

    def quick_extract_prices(self, page: PageContent) -> list[CourseFact]:
        facts = []

        for pattern, fact_type in PRICE_PATTERNS:
            for match in pattern.finditer(page.text[:30000]):
                raw = match.group(0)
                if fact_type == "price_per_course" and match.lastindex and match.lastindex >= 2:
                    amount = str(float(match.group(1).replace(",", "")) + float(match.group(2).replace(",", "")))
                else:
                    amount = match.group(1).replace(",", "")

                try:
                    value = float(amount)
                except ValueError:
                    continue

                facts.append(CourseFact(
                    fact_type=fact_type,
                    value_number=value,
                    value_text=raw,
                    source_url=page.url,
                    source_title=page.title,
                    source_snippet=raw,
                    confidence=0.35,
                ))

        return facts[:10]

    async def resolve_price(
        self,
        school_name: str,
        program_name=None,
        course_code=None,
    ) -> list[CourseFact]:
        queries = self.search_agent.build_price_queries(
            school_name=school_name,
            program_name=program_name,
            course_code=course_code,
        )

        all_facts: list[CourseFact] = []

        for query in queries[:5]:
            try:
                results = await self.search_agent.search(query, max_results=5)
            except Exception:
                continue

            for result in results[:3]:
                try:
                    page = await self.crawler.fetch(result.url)
                except Exception:
                    continue

                if self.llm_client is None:
                    all_facts.extend(self.quick_extract_prices(page))
                else:
                    facts = await self._llm_extract_price(page, school_name, course_code)
                    all_facts.extend(facts)

        return self._dedupe_facts(all_facts)

    async def _llm_extract_price(
        self,
        page: PageContent,
        school_name: str,
        course_code,
    ) -> list[CourseFact]:
        prompt = {
            "task": "extract_course_price",
            "school_name": school_name,
            "course_code": course_code,
            "url": page.url,
            "title": page.title,
            "text": page.text[:18000],
            "instructions": (
                "Extract tuition or price information relevant to online, undergraduate, "
                "non-degree, visiting, guest, or non-matriculated students. "
                "Distinguish per-credit, per-course, resident, non-resident, online fees, "
                "transcript fees, application fees, and unclear price candidates. "
                "Return JSON facts array. Each fact must include fact_type, value_number, "
                "value_text, value_json, source_snippet, confidence."
            ),
        }

        result = await self.llm_client.json(prompt)
        facts = []

        for item in result.get("facts", []):
            facts.append(CourseFact(
                fact_type=item.get("fact_type"),
                value_text=item.get("value_text"),
                value_number=item.get("value_number"),
                value_json=item.get("value_json"),
                source_url=page.url,
                source_title=page.title,
                source_snippet=item.get("source_snippet"),
                confidence=float(item.get("confidence", 0.0)),
            ))

        return facts

    def _dedupe_facts(self, facts: list[CourseFact]) -> list[CourseFact]:
        seen = set()
        result = []

        for fact in facts:
            key = (
                fact.fact_type,
                fact.value_text,
                fact.value_number,
                fact.source_url,
            )
            if key not in seen:
                seen.add(key)
                result.append(fact)

        return result
