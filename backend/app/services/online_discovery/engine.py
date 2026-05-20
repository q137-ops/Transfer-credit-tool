from collections import deque

from .classifier import PageClassifier
from .crawler import Crawler
from .eligibility import EligibilityJudge
from .extractor import CourseExtractor
from .fact_merger import FactMerger
from .local_fuzzy import rank_links
from .models import CourseFact, DiscoveryResult, PageContent
from .price_resolver import PriceResolver
from .search_agent import SearchAgent


class OnlineCourseDiscoveryEngine:
    def __init__(
        self,
        search_agent: SearchAgent,
        crawler: Crawler,
        classifier: PageClassifier,
        extractor: CourseExtractor,
        eligibility_judge: EligibilityJudge,
        price_resolver: PriceResolver,
        fact_merger: FactMerger,
        max_pages_per_school: int = 40,
        max_link_depth: int = 2,
    ):
        self.search_agent = search_agent
        self.crawler = crawler
        self.classifier = classifier
        self.extractor = extractor
        self.eligibility_judge = eligibility_judge
        self.price_resolver = price_resolver
        self.fact_merger = fact_merger
        self.max_pages_per_school = max_pages_per_school
        self.max_link_depth = max_link_depth

    async def discover_school(self, school_name: str) -> DiscoveryResult:
        self.classifier.school_name = school_name

        program_pages = []
        all_courses = []
        missing_tasks = []
        visited_urls = set()
        queued_urls = set()
        price_cache: dict[str, list[CourseFact]] = {}
        page_fact_cache: dict[str, list[CourseFact]] = {}
        queue = deque()

        for query in self.search_agent.build_school_queries(school_name)[:10]:
            try:
                results = await self.search_agent.search(query, max_results=8)
            except Exception:
                continue

            for result in results:
                if result.url in queued_urls:
                    continue
                queued_urls.add(result.url)
                queue.append((result.url, 0, "search", result.title, result.snippet))

        while queue and len(visited_urls) < self.max_pages_per_school:
            url, depth, discovered_by, source_title, source_snippet = queue.popleft()

            if url in visited_urls:
                continue

            visited_urls.add(url)

            try:
                page = await self.crawler.fetch(url)
            except Exception:
                continue

            classification = await self.classifier.classify(page)

            if self._should_keep_program_page(classification):
                program_pages.append({
                    "url": page.url,
                    "title": page.title,
                    "page_type": classification.page_type,
                    "confidence": classification.confidence,
                    "evidence": classification.evidence,
                    "discovered_by": discovered_by,
                    "source_title": source_title,
                    "source_snippet": source_snippet,
                    "raw": classification.raw,
                })

                page_facts = page_fact_cache.get(page.url)
                if page_facts is None:
                    page_facts = await self.eligibility_judge.judge(page)
                    page_fact_cache[page.url] = page_facts

                extracted_courses = await self.extractor.extract_courses(page)

                for course in extracted_courses:
                    price_key = course.course_code or page.url
                    price_facts = price_cache.get(price_key)

                    if price_facts is None:
                        price_facts = self._course_price_facts(course.raw, page)

                        if course.course_code and not price_facts:
                            price_facts.extend(await self.price_resolver.resolve_price(
                                school_name=school_name,
                                program_name=page.title,
                                course_code=course.course_code,
                            ))

                        price_cache[price_key] = price_facts

                    facts = page_facts + price_facts
                    summary = self.fact_merger.summarize(facts)

                    course_obj = {
                        "school_name": school_name,
                        "course_code": course.course_code,
                        "course_title": course.course_title,
                        "credits": course.credits,
                        "canonical_course_url": course.canonical_course_url,
                        "delivery_mode": course.delivery_mode,
                        "confidence": course.confidence,
                        "facts_summary": summary,
                        "raw": course.raw,
                    }

                    all_courses.append(course_obj)

                    for missing in summary["missing"]:
                        missing_tasks.append({
                            "school_name": school_name,
                            "course_code": course.course_code,
                            "task_type": f"resolve_{missing}",
                            "query": self._build_missing_query(
                                school_name=school_name,
                                course_code=course.course_code,
                                missing=missing,
                            ),
                        })

            if depth >= self.max_link_depth:
                continue

            for link in rank_links(page, school_name=school_name, limit=12):
                if link["url"] in visited_urls or link["url"] in queued_urls:
                    continue

                queued_urls.add(link["url"])
                queue.append((link["url"], depth + 1, f"link_depth_{depth + 1}", link.get("text", ""), str(link)))

        return DiscoveryResult(
            school_name=school_name,
            program_pages=self._dedupe_program_pages(program_pages),
            courses=self._dedupe_courses(all_courses),
            missing_tasks=missing_tasks,
        )

    def _should_keep_program_page(self, classification) -> bool:
        if not classification.is_target_candidate:
            return False

        if classification.is_degree_only or classification.is_non_credit:
            return False

        return True

    def _course_price_facts(self, raw: dict, page: PageContent) -> list[CourseFact]:
        facts = []

        for item in raw.get("price_candidates", []):
            basis = item.get("basis", "")
            fact_type = "price_candidate"

            if "credit" in basis:
                fact_type = "price_per_credit"
            elif "course" in basis:
                fact_type = "price_per_course"

            facts.append(CourseFact(
                fact_type=fact_type,
                value_text=item.get("value_text"),
                value_number=item.get("value_number"),
                value_json={"basis": basis},
                source_url=page.url,
                source_title=page.title,
                source_snippet=item.get("value_text"),
                confidence=0.5,
            ))

        return facts

    def _dedupe_program_pages(self, pages: list[dict]) -> list[dict]:
        seen = set()
        result = []

        for page in pages:
            url = page.get("url")
            if url in seen:
                continue
            seen.add(url)
            result.append(page)

        return result

    def _dedupe_courses(self, courses: list[dict]) -> list[dict]:
        seen = set()
        result = []

        for course in courses:
            key = (
                course.get("school_name"),
                course.get("course_code"),
                course.get("course_title"),
                course.get("canonical_course_url"),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(course)

        return result

    def _build_missing_query(self, school_name: str, course_code, missing: str) -> str:
        if missing == "price":
            return f'{school_name} "{course_code or ""}" online non-degree tuition price'

        if missing == "registration_url":
            return f'{school_name} "{course_code or ""}" enroll online course'

        if missing == "is_non_degree_accessible":
            return f'{school_name} non-degree visiting student online courses credit'

        if missing == "is_academic_credit":
            return f'{school_name} "{course_code or ""}" academic credit online course'

        if missing == "is_online":
            return f'{school_name} "{course_code or ""}" online course'

        return f'{school_name} "{course_code or ""}" {missing}'
