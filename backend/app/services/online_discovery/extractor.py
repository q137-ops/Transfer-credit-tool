import re

from .models import ExtractedCourse, PageContent


COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{2,6}\s?\d{3,4}[A-Z]?\b")
CREDITS_PATTERN = re.compile(
    r"(?P<credits>\d(?:\.\d)?)\s*(?:semester\s*)?(?:credit|credits|credit hours|hours|units)\b",
    re.I,
)
PRICE_PATTERN = re.compile(
    r"\$\s?(?P<amount>\d{2,5}(?:,\d{3})?(?:\.\d{2})?)\s*(?P<basis>per credit|/credit|per course|course fee)?",
    re.I,
)
COMBINED_PRICE_PATTERN = re.compile(
    r"\$\s?(?P<first>\d{2,5}(?:,\d{3})?(?:\.\d{2})?)\s*\+\s*\$\s?(?P<second>\d{2,5}(?:,\d{3})?(?:\.\d{2})?)",
    re.I,
)


class CourseExtractor:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def quick_extract_courses(self, page: PageContent) -> list[ExtractedCourse]:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        courses: dict[str, ExtractedCourse] = {}

        for index, line in enumerate(lines):
            matches = list(COURSE_CODE_PATTERN.finditer(line))

            for match_index, match in enumerate(matches):
                code = " ".join(match.group(0).split())
                next_match_start = (
                    matches[match_index + 1].start()
                    if match_index + 1 < len(matches)
                    else None
                )
                segment = line[match.start():next_match_start].strip()
                tail = [] if next_match_start is not None else lines[index + 1: index + 4]
                window = " ".join([segment] + tail)
                title = self._extract_title(line, match.end())
                if not title and index > 0:
                    title = self._clean_title_line(lines[index - 1])
                credits = self._extract_credits(window)
                price_candidates = self._extract_prices(window)

                current = courses.get(code)
                confidence = 0.45
                if title:
                    confidence += 0.15
                if credits is not None:
                    confidence += 0.15
                if "online" in window.lower():
                    confidence += 0.1

                candidate = ExtractedCourse(
                    course_code=code,
                    course_title=title,
                    credits=credits,
                    canonical_course_url=page.url,
                    delivery_mode="online" if "online" in window.lower() else None,
                    confidence=min(confidence, 0.85),
                    evidence=window[:500],
                    raw={"line": line, "window": window, "price_candidates": price_candidates},
                )

                if current is None or candidate.confidence > current.confidence:
                    courses[code] = candidate

        return list(courses.values())[:250]

    def quick_extract_codes(self, page: PageContent) -> list[str]:
        return [course.course_code for course in self.quick_extract_courses(page) if course.course_code]

    def _extract_title(self, line: str, code_end: int) -> str:
        title = line[code_end:].strip(" -:|")
        title = re.split(r"\b\d(?:\.\d)?\s*(?:credit|credits|hours|units)\b", title, flags=re.I)[0]
        title = PRICE_PATTERN.split(title)[0] if "$" in title else title
        return self._clean_title_line(title)

    def _clean_title_line(self, line: str) -> str:
        title = re.sub(r"^#+\s*", "", line).strip()
        title = re.sub(r"\b(New|General Education|Major-Specific Electives|International|Visa Gap|OHS)\b", "", title)
        title = re.sub(r"\s{2,}", " ", title).strip(" -:|")
        return title[:180]

    def _extract_credits(self, text: str):
        match = CREDITS_PATTERN.search(text)

        if not match:
            return None

        try:
            return float(match.group("credits"))
        except ValueError:
            return None

    def _extract_prices(self, text: str) -> list[dict]:
        prices = []

        for match in COMBINED_PRICE_PATTERN.finditer(text):
            first = match.group("first").replace(",", "")
            second = match.group("second").replace(",", "")

            try:
                value = float(first) + float(second)
            except ValueError:
                continue

            prices.append({
                "value_number": value,
                "value_text": match.group(0),
                "basis": "per course",
                "components": [float(first), float(second)],
            })

        for match in PRICE_PATTERN.finditer(text):
            amount = match.group("amount").replace(",", "")

            try:
                value = float(amount)
            except ValueError:
                continue

            prices.append({
                "value_number": value,
                "value_text": match.group(0),
                "basis": (match.group("basis") or "unknown").lower(),
            })

        return prices[:5]

    async def extract_courses(self, page: PageContent) -> list[ExtractedCourse]:
        if self.llm_client is None:
            return self.quick_extract_courses(page)

        prompt = {
            "task": "extract_online_courses",
            "url": page.url,
            "title": page.title,
            "text": page.text[:20000],
            "instructions": (
                "Extract academic-credit online course information if present. "
                "Do not extract degree programs, certificates, bootcamps, or non-credit courses. "
                "Return JSON with a courses array. Each course should include course_code, "
                "course_title, credits, canonical_course_url, delivery_mode, confidence, evidence."
            ),
        }

        result = await self.llm_client.json(prompt)
        courses = []

        for item in result.get("courses", []):
            courses.append(
                ExtractedCourse(
                    course_code=item.get("course_code"),
                    course_title=item.get("course_title") or "",
                    credits=item.get("credits"),
                    canonical_course_url=item.get("canonical_course_url") or page.url,
                    delivery_mode=item.get("delivery_mode"),
                    confidence=float(item.get("confidence", 0.0)),
                    evidence=item.get("evidence", ""),
                    raw=item,
                )
            )

        return courses
