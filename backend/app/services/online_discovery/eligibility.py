from .local_fuzzy import rank_links
from .models import CourseFact, PageContent


ONLINE_TERMS = ["online", "fully online", "distance education", "distance learning", "web-based"]
CREDIT_TERMS = ["academic credit", "college credit", "semester credit", "credit hours", "transcript"]
NON_DEGREE_TERMS = [
    "non-degree",
    "nondegree",
    "non-matriculated",
    "visiting student",
    "guest student",
    "transient student",
    "special student",
]
REGISTRATION_TERMS = ["register", "registration", "enroll", "apply", "admissions"]


class EligibilityJudge:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def judge(self, page: PageContent) -> list[CourseFact]:
        if self.llm_client is None:
            text = page.text.lower()
            facts = []

            self._append_keyword_fact(
                facts,
                page,
                "is_online",
                ONLINE_TERMS,
                text,
                "Keyword-based detection for online delivery.",
                0.55,
            )
            self._append_keyword_fact(
                facts,
                page,
                "is_academic_credit",
                CREDIT_TERMS,
                text,
                "Keyword-based detection for academic credit.",
                0.55,
            )
            self._append_keyword_fact(
                facts,
                page,
                "is_non_degree_accessible",
                NON_DEGREE_TERMS,
                text,
                "Keyword-based detection for non-degree access.",
                0.55,
            )

            ranked_registration_links = rank_links(page, school_name="", limit=8, min_score=4.0)
            direct_registration_links = [
                link for link in page.links
                if any(term in f"{link.get('text', '')} {link.get('url', '')}".lower() for term in REGISTRATION_TERMS)
            ][:8]

            for link in ranked_registration_links + direct_registration_links:
                link_text = f"{link.get('text', '')} {link.get('url', '')}".lower()
                if any(term in link_text for term in REGISTRATION_TERMS):
                    facts.append(CourseFact(
                        fact_type="registration_url",
                        value_text=link["url"],
                        source_url=page.url,
                        source_title=page.title,
                        source_snippet=link.get("text", ""),
                        confidence=0.45,
                    ))

            return facts

        prompt = {
            "task": "judge_online_course_eligibility",
            "url": page.url,
            "title": page.title,
            "text": page.text[:16000],
            "instructions": (
                "Determine whether the page provides evidence for online delivery, "
                "academic credit, non-degree accessibility, degree-only restriction, "
                "registration path, and transcripted credit. Return JSON facts array. "
                "Each fact must include fact_type, value_text, source_snippet, confidence."
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

    def _append_keyword_fact(
        self,
        facts: list[CourseFact],
        page: PageContent,
        fact_type: str,
        terms: list[str],
        text: str,
        snippet_prefix: str,
        confidence: float,
    ) -> None:
        matches = [term for term in terms if term in text]

        if not matches:
            return

        facts.append(CourseFact(
            fact_type=fact_type,
            value_text="true",
            source_url=page.url,
            source_title=page.title,
            source_snippet=f"{snippet_prefix} Matches: {', '.join(matches[:5])}",
            confidence=confidence,
        ))
