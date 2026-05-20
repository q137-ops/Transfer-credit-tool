import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.online_discovery.models import DiscoveryResult  # noqa: E402
from app.services.online_discovery.repository import OnlineDiscoveryRepository  # noqa: E402


load_dotenv(ROOT / ".env")

ASU_CATALOG_JS = (
    "https://courses.ulc.asu.edu/assets/js/"
    "page--src--pages--index-vue~page--src--templates--courses-vue.b9893600.js"
)
ASU_PROGRAM_URL = "https://ulc.asu.edu/"
ASU_PRICING_URL = "https://ulc.asu.edu/how-to-enroll/pricing/"
ASU_ENROLL_URL = "https://ulc.asu.edu/how-to-enroll/"
BYU_PROGRAM_URL = "https://is.byu.edu/university"
BYU_CATALOG_API = "https://cereg.byu.edu/is/catalog/api/catalog"
CSCC_ONLINE_URL = "https://www.cscc.edu/academics/online-learning/"
CSCC_COURSE_LISTING_URL = "https://web.cscc.edu/courselisting/DistanceLearning.aspx?term=26SU"
CSCC_TUITION_URL = "https://www.cscc.edu/academics/tuition-and-fees/index.shtml"
CSCC_REGISTER_URL = "https://www.cscc.edu/academics/courses/index.shtml"
CSCC_OHIO_PRICE_PER_CREDIT = 192.93
CSCC_NON_OHIO_PRICE_PER_CREDIT = 394.59
CSCC_INTERNATIONAL_PRICE_PER_CREDIT = 468.15
KEISER_CATALOG_URL = "https://www.keiseruniversity.edu/catalog/"
KEISER_TUITION_URL = "https://www.keiseruniversity.edu/financial-services/tuition/"
KEISER_ONLINE_URL = "https://www.keiseronline.com/bachelors-degrees/"


def make_summary(
    *,
    source_url: str,
    source_title: str,
    registration_url: str,
    price_text: str,
    price_number: float,
    price_fact_type: str = "price_per_course",
) -> dict[str, Any]:
    return {
        "status": "confirmed_or_likely_available",
        "missing": [],
        "best_facts": {
            "is_online": {
                "value_text": "true",
                "source_url": source_url,
                "source_title": source_title,
                "source_snippet": "Official online course catalog.",
                "confidence": 0.95,
            },
            "is_academic_credit": {
                "value_text": "true",
                "source_url": source_url,
                "source_title": source_title,
                "source_snippet": "Official catalog describes transcripted/transferable credit courses.",
                "confidence": 0.95,
            },
            "is_non_degree_accessible": {
                "value_text": "true",
                "source_url": source_url,
                "source_title": source_title,
                "source_snippet": "Official page says admission/application is not required for this pathway.",
                "confidence": 0.9,
            },
            "registration_url": {
                "value_text": registration_url,
                "source_url": source_url,
                "source_title": source_title,
                "source_snippet": "Official enrollment or course purchase page.",
                "confidence": 0.9,
            },
            price_fact_type: {
                "value_text": price_text,
                "value_number": price_number,
                "source_url": source_url,
                "source_title": source_title,
                "source_snippet": price_text,
                "confidence": 0.95,
            },
        },
    }


def make_cscc_summary(
    *,
    registration_url: str,
    credits: float,
) -> dict[str, Any]:
    ohio_total = round(credits * CSCC_OHIO_PRICE_PER_CREDIT, 2)
    return {
        "status": "confirmed_or_likely_available",
        "missing": [],
        "best_facts": {
            "is_online": {
                "value_text": "true",
                "source_url": CSCC_ONLINE_URL,
                "source_title": "Online Learning | Columbus State Community College",
                "source_snippet": "Official page states students can choose online courses.",
                "confidence": 0.85,
            },
            "is_academic_credit": {
                "value_text": "true",
                "source_url": CSCC_COURSE_LISTING_URL,
                "source_title": "Summer 2026 Distance Learning Courses | Columbus State Community College",
                "source_snippet": "Official credit-course distance learning section listing.",
                "confidence": 0.9,
            },
            "is_non_degree_accessible": {
                "value_text": "true",
                "source_url": "https://www.cscc.edu/academics/transient-guest",
                "source_title": "Guest Students | Columbus State Community College",
                "source_snippet": "Official page says guest/transient students can take classes and transfer them back.",
                "confidence": 0.8,
            },
            "registration_url": {
                "value_text": registration_url,
                "source_url": CSCC_REGISTER_URL,
                "source_title": "Course Descriptions & Schedules | Columbus State Community College",
                "source_snippet": "Official course schedule and registration information.",
                "confidence": 0.85,
            },
            "price_per_credit": {
                "value_text": (
                    "$192.93 per credit hour for Ohio residents; "
                    "$394.59 non-Ohio U.S.; $468.15 international"
                ),
                "value_number": CSCC_OHIO_PRICE_PER_CREDIT,
                "value_json": {
                    "ohio_resident": CSCC_OHIO_PRICE_PER_CREDIT,
                    "non_ohio_us": CSCC_NON_OHIO_PRICE_PER_CREDIT,
                    "international": CSCC_INTERNATIONAL_PRICE_PER_CREDIT,
                },
                "source_url": CSCC_TUITION_URL,
                "source_title": "Tuition & Fees | Columbus State Community College",
                "source_snippet": "Official Autumn 2025 - Spring 2026 per-credit rates.",
                "confidence": 0.95,
            },
            "price_per_course": {
                "value_text": f"Estimated Ohio resident tuition/fees for {credits:g} credits: ${ohio_total:,.2f}",
                "value_number": ohio_total,
                "value_json": {
                    "credits": credits,
                    "rate_basis": "Ohio resident per-credit fee",
                },
                "source_url": CSCC_TUITION_URL,
                "source_title": "Tuition & Fees | Columbus State Community College",
                "source_snippet": "Estimated by multiplying official per-credit rate by course credits.",
                "confidence": 0.85,
            },
        },
    }


def extract_json_object(text: str, start: int, preferred_prefix: str = "{") -> Optional[dict[str, Any]]:
    obj_start = text.rfind(preferred_prefix, 0, start)
    if obj_start < 0 and preferred_prefix != "{":
        obj_start = text.rfind("{", 0, start)

    while obj_start >= 0:
        depth = 0
        in_string = False
        escaped = False

        for pos in range(obj_start, len(text)):
            char = text[pos]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[obj_start: pos + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

        obj_start = text.rfind(preferred_prefix, 0, obj_start)
        if obj_start < 0 and preferred_prefix != "{":
            obj_start = text.rfind("{", 0, obj_start)

    return None


def extract_object_with_id(text: str, start: int, expected_id: str) -> Optional[dict[str, Any]]:
    obj_start = text.rfind("{", 0, start)
    attempts = 0

    while obj_start >= 0 and attempts < 300:
        attempts += 1
        item = extract_json_object(text, obj_start)
        if item and item.get("id") == expected_id:
            return item
        obj_start = text.rfind("{", 0, obj_start)

    return None


def extract_balanced_segment(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escaped = False

    for pos in range(start, len(text)):
        char = text[pos]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start: pos + 1]

    return text[start:]


def js_field(segment: str, field: str) -> str:
    match = re.search(rf'"{re.escape(field)}":"((?:\\.|[^"\\])*)"', segment)
    if not match:
        return ""
    return match.group(1).replace('\\"', '"').replace("\\/", "/")


def fetch_asu() -> DiscoveryResult:
    text = httpx.get(ASU_CATALOG_JS, timeout=40.0).text
    courses = []
    seen = set()

    for match in re.finditer(r'"id":"([A-Z]{2,6} \d{3}[A-Z]?)"', text):
        code = match.group(1)
        if not code or code in seen:
            continue

        seen.add(code)
        start = text.rfind("{", 0, match.start())
        segment = extract_balanced_segment(text, start)
        content = js_field(segment, "content")
        credits_match = re.search(r"Credits available:\s*(\d+(?:\.\d+)?)", content)
        credits = float(credits_match.group(1)) if credits_match else None
        path = js_field(segment, "path")
        url = f"https://courses.ulc.asu.edu/{path}/" if path else ASU_PROGRAM_URL
        title = js_field(segment, "title") or js_field(segment, "subtitle")

        courses.append({
            "school_name": "Arizona State University",
            "course_code": code,
            "course_title": title,
            "credits": credits,
            "canonical_course_url": url,
            "delivery_mode": "online",
            "confidence": 0.92,
            "facts_summary": make_summary(
                source_url=ASU_PRICING_URL,
                source_title="Pricing | ASU Universal Learner Courses",
                registration_url=ASU_ENROLL_URL,
                price_text="$25 enrollment fee + $400 credit conversion fee; total per course: $425",
                price_number=425.0,
            ),
            "raw": {
                "id": code,
                "path": path,
                "content": content,
            },
        })

    return DiscoveryResult(
        school_name="Arizona State University",
        program_pages=[{
            "url": ASU_PROGRAM_URL,
            "title": "ASU Universal Learner Courses",
            "page_type": "target_program_page",
            "confidence": 0.95,
            "evidence": "Official ASU ULC pages state online college-level courses, no application required, $25 enrollment fee, $400 credit conversion fee.",
            "discovered_by": "official_catalog_import",
            "raw": {"pricing_url": ASU_PRICING_URL, "enroll_url": ASU_ENROLL_URL},
        }],
        courses=courses,
        missing_tasks=[],
    )


def fetch_byu() -> DiscoveryResult:
    data = httpx.get(BYU_CATALOG_API, timeout=40.0).json()
    courses = []

    for item in data.get("courseDescriptions", []):
        school_types = item.get("schoolTypes") or []
        if "University" not in school_types:
            continue

        code = item.get("departmentCatalog")
        route = item.get("courseRoute") or ""
        url = f"https://is.byu.edu/catalog/{route}" if route else BYU_PROGRAM_URL
        amount = item.get("amount")
        credits = item.get("academicCreditHours")
        price_text = f"${amount:,.2f}" if isinstance(amount, (int, float)) else ""

        courses.append({
            "school_name": "Brigham Young University",
            "course_code": code,
            "course_title": item.get("title") or "",
            "credits": credits,
            "canonical_course_url": url,
            "delivery_mode": "online",
            "confidence": 0.9,
            "facts_summary": make_summary(
                source_url=BYU_PROGRAM_URL,
                source_title="University Courses Online | BYU Independent Study",
                registration_url=url,
                price_text=price_text,
                price_number=float(amount) if isinstance(amount, (int, float)) else 0.0,
            ),
            "raw": item,
        })

    return DiscoveryResult(
        school_name="Brigham Young University",
        program_pages=[{
            "url": BYU_PROGRAM_URL,
            "title": "University Courses Online | BYU Independent Study",
            "page_type": "target_program_page",
            "confidence": 0.95,
            "evidence": "Official BYU Independent Study university page states BYU admission is not required, enrollment is anytime, and credits are transferable.",
            "discovered_by": "official_catalog_import",
            "raw": {"catalog_api": BYU_CATALOG_API},
        }],
        courses=courses,
        missing_tasks=[],
    )


def fetch_cscc() -> DiscoveryResult:
    html = httpx.get(CSCC_COURSE_LISTING_URL, timeout=60.0).text
    soup = BeautifulSoup(html, "html.parser")
    courses_by_code: dict[str, dict[str, Any]] = {}

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 10 or not tds[0].find("a"):
            continue

        cells = [td.get_text(" ", strip=True).replace("\xa0", " ") for td in tds]
        code_match = re.search(r"\b[A-Z]{2,6}-\d{3,4}\b", cells[0])
        if not code_match:
            continue

        location = cells[8]
        if "Web" not in location:
            continue

        code_dash = code_match.group(0)
        code = code_dash.replace("-", " ")
        title = cells[1]
        credits = float(cells[6]) if re.match(r"^\d+(?:\.\d+)?$", cells[6]) else 0.0
        canonical_url = f"https://explore.cscc.edu/courses/{code_dash.replace('-', '')}"
        registration_url = (
            "https://selfservice.cscc.edu/Student/Student/Courses/Search?"
            f"keyword={code_dash}"
        )

        existing = courses_by_code.setdefault(code, {
            "school_name": "Columbus State Community College",
            "course_code": code,
            "course_title": title,
            "credits": credits,
            "canonical_course_url": canonical_url,
            "delivery_mode": "online",
            "confidence": 0.86,
            "facts_summary": make_cscc_summary(
                registration_url=registration_url,
                credits=credits,
            ),
            "raw": {
                "source": CSCC_COURSE_LISTING_URL,
                "sections": [],
            },
        })

        existing["raw"]["sections"].append({
            "course_section": cells[0],
            "instruction_method": cells[2],
            "days": cells[3],
            "meeting_time": cells[4],
            "dates": cells[5],
            "location": location,
            "seats_available": cells[9],
        })

    return DiscoveryResult(
        school_name="Columbus State Community College",
        program_pages=[{
            "url": CSCC_ONLINE_URL,
            "title": "Online Learning | Columbus State Community College",
            "page_type": "course_list_page",
            "confidence": 0.9,
            "evidence": "Official CSCC online learning page and distance-learning course section listing confirm online/web credit course offerings.",
            "discovered_by": "official_catalog_import",
            "raw": {
                "course_listing_url": CSCC_COURSE_LISTING_URL,
                "tuition_url": CSCC_TUITION_URL,
                "register_url": CSCC_REGISTER_URL,
            },
        }],
        courses=list(courses_by_code.values()),
        missing_tasks=[],
    )


def fetch_keiser() -> DiscoveryResult:
    return DiscoveryResult(
        school_name="Keiser University",
        program_pages=[{
            "url": KEISER_CATALOG_URL,
            "title": "Keiser University Catalogs",
            "page_type": "degree_program_page",
            "confidence": 0.75,
            "evidence": (
                "Official pages confirm online degree/program catalog and tuition calculator, "
                "but I did not find official evidence of open-enrollment non-degree individual online credit courses."
            ),
            "discovered_by": "official_catalog_import",
            "raw": {
                "catalog_url": KEISER_CATALOG_URL,
                "tuition_url": KEISER_TUITION_URL,
                "online_programs_url": KEISER_ONLINE_URL,
                "availability_status": "no_confirmed_online_non_degree_individual_credit_courses",
            },
        }],
        courses=[],
        missing_tasks=[{
            "school_name": "Keiser University",
            "course_code": None,
            "task_type": "manual_review_online_non_degree_credit_courses",
            "query": "Keiser University online non-degree individual credit courses tuition",
        }],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--school",
        choices=["asu", "byu", "cscc", "keiser", "both", "all"],
        default="both",
    )
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    selected = []
    if args.school in ("asu", "both", "all"):
        selected.append(fetch_asu())
    if args.school in ("byu", "both", "all"):
        selected.append(fetch_byu())
    if args.school in ("cscc", "all"):
        selected.append(fetch_cscc())
    if args.school in ("keiser", "all"):
        selected.append(fetch_keiser())

    repository = OnlineDiscoveryRepository()

    for result in selected:
        run_id = None
        if not args.no_persist:
            run_id = repository.save_result(
                result=result,
                use_ai=False,
                max_pages=1,
                max_depth=0,
            )

        print(
            f"{result.school_name}: run_id={run_id or 'not_persisted'} "
            f"program_pages={len(result.program_pages)} courses={len(result.courses)}"
        )
        for course in result.courses[:8]:
            summary = course["facts_summary"]["best_facts"]
            price = summary.get("price_per_course", {})
            print(
                f"  {course['course_code']} | {course['course_title']} | "
                f"{course['credits']} credits | {price.get('value_text')} | "
                f"{course['canonical_course_url']}"
            )


if __name__ == "__main__":
    main()
