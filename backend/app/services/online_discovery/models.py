from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass
class PageContent:
    url: str
    title: str
    text: str
    html: Optional[str] = None
    links: list[dict[str, str]] = field(default_factory=list)


@dataclass
class PageClassification:
    page_type: str
    is_official: bool
    is_target_candidate: bool
    is_degree_only: bool
    is_non_credit: bool
    confidence: float
    evidence: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedCourse:
    course_code: Optional[str]
    course_title: str
    credits: Optional[float]
    canonical_course_url: Optional[str]
    delivery_mode: Optional[str]
    confidence: float
    evidence: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CourseFact:
    fact_type: str
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_json: Optional[dict[str, Any]] = None
    source_url: str = ""
    source_title: Optional[str] = None
    source_snippet: Optional[str] = None
    confidence: float = 0.0


@dataclass
class DiscoveryResult:
    school_name: str
    program_pages: list[dict[str, Any]]
    courses: list[dict[str, Any]]
    missing_tasks: list[dict[str, Any]]
