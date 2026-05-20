from .local_fuzzy import NEGATIVE_PHRASES, PROGRAM_PHRASES, score_page
from .models import PageClassification, PageContent


DEGREE_ONLY_RED_FLAGS = [
    "degree-seeking students",
    "admitted to the program",
    "online bachelor's",
    "online bachelor",
    "online master's",
    "online master",
    "mba program",
    "program admission required",
    "students admitted to",
    "major requirements",
]

NON_CREDIT_RED_FLAGS = [
    "non-credit",
    "noncredit",
    "ceu",
    "continuing education units",
    "certificate of completion",
    "professional development",
    "bootcamp",
    "workforce training",
    "not for academic credit",
]

TARGET_GREEN_FLAGS = list(PROGRAM_PHRASES.keys())


class PageClassifier:
    def __init__(self, llm_client=None, school_name: str = ""):
        self.llm_client = llm_client
        self.school_name = school_name

    def quick_score(self, page: PageContent) -> dict:
        fuzzy = score_page(page, school_name=self.school_name)
        text = f"{page.url}\n{page.title}\n{page.text[:5000]}".lower()

        degree_hits = [x for x in DEGREE_ONLY_RED_FLAGS if x in text]
        non_credit_hits = [x for x in NON_CREDIT_RED_FLAGS if x in text]
        green_hits = [x for x in TARGET_GREEN_FLAGS if x in text]

        return {
            "score": fuzzy.score,
            "green_hits": sorted(set(green_hits + fuzzy.positive_hits)),
            "degree_hits": degree_hits,
            "non_credit_hits": sorted(set(non_credit_hits + [
                hit for hit in fuzzy.negative_hits if hit in NEGATIVE_PHRASES
            ])),
            "signals": fuzzy.signals,
        }

    async def classify(self, page: PageContent) -> PageClassification:
        quick = self.quick_score(page)

        if self.llm_client is None:
            has_negative = bool(quick["degree_hits"] or quick["non_credit_hits"])
            is_target = quick["score"] >= 18 and not has_negative

            if quick["degree_hits"]:
                page_type = "degree_program_page"
            elif quick["non_credit_hits"]:
                page_type = "non_credit_training_page"
            elif is_target and any(hit in quick["green_hits"] for hit in ["course search", "course schedule", "class schedule", "course catalog"]):
                page_type = "course_list_page"
            elif is_target:
                page_type = "target_candidate_page"
            else:
                page_type = "irrelevant_or_needs_review"

            confidence = min(max((quick["score"] + 20) / 100, 0.05), 0.95)

            return PageClassification(
                page_type=page_type,
                is_official=True,
                is_target_candidate=is_target,
                is_degree_only=bool(quick["degree_hits"]),
                is_non_credit=bool(quick["non_credit_hits"]),
                confidence=confidence,
                evidence=str(quick),
                raw={"quick": quick},
            )

        prompt = {
            "task": "classify_university_course_page",
            "url": page.url,
            "title": page.title,
            "text": page.text[:12000],
            "allowed_page_types": [
                "target_program_page",
                "course_list_page",
                "course_detail_page",
                "tuition_fee_page",
                "registration_instruction_page",
                "degree_program_page",
                "general_catalog_page",
                "non_credit_training_page",
                "irrelevant_page",
            ],
            "instructions": (
                "Classify the page for an online credit course discovery engine. "
                "We need pages that help determine whether a non-degree student can take "
                "online academic-credit courses. Return JSON only."
            ),
        }

        result = await self.llm_client.json(prompt)

        return PageClassification(
            page_type=result.get("page_type", "unknown"),
            is_official=result.get("is_official", False),
            is_target_candidate=result.get("is_target_candidate", False),
            is_degree_only=result.get("is_degree_only", False),
            is_non_credit=result.get("is_non_credit", False),
            confidence=float(result.get("confidence", 0.0)),
            evidence=result.get("evidence", ""),
            raw=result,
        )
