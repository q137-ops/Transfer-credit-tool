import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urlparse

from .models import PageContent


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


PROGRAM_PHRASES = {
    "online": 12,
    "fully online": 16,
    "online courses": 18,
    "universal learner": 24,
    "universal learner courses": 28,
    "credit conversion fee": 18,
    "add it to your transcript": 16,
    "independent study": 18,
    "independent study university": 24,
    "byu admission not required": 20,
    "no byu admission necessary": 20,
    "transferable credits": 18,
    "distance learning": 8,
    "academic credit": 18,
    "college credit": 16,
    "semester credit": 14,
    "credit hours": 10,
    "non-degree": 18,
    "nondegree": 18,
    "non-matriculated": 18,
    "visiting student": 18,
    "guest student": 16,
    "transient student": 14,
    "special student": 12,
    "open enrollment": 10,
    "registration": 6,
    "enroll": 6,
}

COURSE_LIST_PHRASES = {
    "course search": 15,
    "course schedule": 15,
    "class schedule": 14,
    "course catalog": 12,
    "course list": 14,
    "shop courses": 10,
    "purchase a course": 10,
    "courses": 6,
    "subject": 4,
    "credits": 8,
    "credit hours": 10,
    "tuition": 5,
}

NEGATIVE_PHRASES = {
    "non-credit": 25,
    "noncredit": 25,
    "not for academic credit": 35,
    "continuing education units": 20,
    "ceu": 15,
    "bootcamp": 20,
    "workforce training": 15,
    "degree-seeking students": 16,
    "admitted to the program": 14,
    "program admission required": 18,
    "online bachelor": 14,
    "online bachelor's": 14,
    "online master": 14,
    "online master's": 14,
}


@dataclass
class LocalScore:
    score: float
    positive_hits: list[str] = field(default_factory=list)
    negative_hits: list[str] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(normalize(text)))


def same_registered_domain(url_a: str, url_b: str) -> bool:
    host_a = urlparse(url_a).netloc.lower().split(":")[0]
    host_b = urlparse(url_b).netloc.lower().split(":")[0]

    if not host_a or not host_b:
        return False

    parts_a = host_a.split(".")
    parts_b = host_b.split(".")
    return parts_a[-2:] == parts_b[-2:]


def phrase_hits(text: str, phrases: dict[str, int]) -> tuple[float, list[str]]:
    normalized = normalize(text)
    hits = [phrase for phrase in phrases if phrase in normalized]
    return float(sum(phrases[phrase] for phrase in hits)), hits


def fuzzy_school_match(school_name: str, text: str) -> float:
    school = normalize(school_name)
    candidate = normalize(text)

    if not school or not candidate:
        return 0.0

    if school in candidate:
        return 20.0

    school_tokens = tokens(school)
    candidate_tokens = tokens(candidate)
    overlap = len(school_tokens & candidate_tokens) / max(len(school_tokens), 1)
    similarity = SequenceMatcher(None, school, candidate[: max(len(school) * 2, 80)]).ratio()
    return max(overlap * 16, similarity * 10)


def score_page(page: PageContent, school_name: str = "") -> LocalScore:
    text = f"{page.url}\n{page.title}\n{page.text[:12000]}"
    program_score, program_hits = phrase_hits(text, PROGRAM_PHRASES)
    course_score, course_hits = phrase_hits(text, COURSE_LIST_PHRASES)
    negative_score, negative_hits = phrase_hits(text, NEGATIVE_PHRASES)
    school_score = fuzzy_school_match(school_name, text) if school_name else 0.0
    score = program_score + course_score + school_score - negative_score

    return LocalScore(
        score=score,
        positive_hits=program_hits + course_hits,
        negative_hits=negative_hits,
        signals={
            "program_score": program_score,
            "course_score": course_score,
            "school_score": school_score,
            "negative_score": negative_score,
        },
    )


def score_link(link: dict[str, str], source_page: PageContent, school_name: str = "") -> LocalScore:
    text = f"{link.get('url', '')}\n{link.get('text', '')}"
    program_score, program_hits = phrase_hits(text, PROGRAM_PHRASES)
    course_score, course_hits = phrase_hits(text, COURSE_LIST_PHRASES)
    negative_score, negative_hits = phrase_hits(text, NEGATIVE_PHRASES)
    school_score = fuzzy_school_match(school_name, text) if school_name else 0.0
    internal_bonus = 8.0 if same_registered_domain(source_page.url, link.get("url", "")) else -12.0
    score = program_score + course_score + school_score + internal_bonus - negative_score

    return LocalScore(
        score=score,
        positive_hits=program_hits + course_hits,
        negative_hits=negative_hits,
        signals={
            "program_score": program_score,
            "course_score": course_score,
            "school_score": school_score,
            "internal_bonus": internal_bonus,
            "negative_score": negative_score,
        },
    )


def rank_links(
    page: PageContent,
    school_name: str,
    limit: int = 12,
    min_score: float = 8.0,
) -> list[dict]:
    ranked = []

    for link in page.links:
        link_score = score_link(link, page, school_name)

        if link_score.score < min_score:
            continue

        ranked.append({
            "url": link["url"],
            "text": link.get("text", ""),
            "score": link_score.score,
            "hits": link_score.positive_hits,
            "negative_hits": link_score.negative_hits,
            "signals": link_score.signals,
        })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
