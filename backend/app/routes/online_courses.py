import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.services.online_discovery.classifier import PageClassifier
from app.services.online_discovery.crawler import Crawler
from app.services.online_discovery.eligibility import EligibilityJudge
from app.services.online_discovery.engine import OnlineCourseDiscoveryEngine
from app.services.online_discovery.extractor import CourseExtractor
from app.services.online_discovery.fact_merger import FactMerger
from app.services.online_discovery.price_resolver import PriceResolver
from app.services.online_discovery.providers import OpenAIJsonClient
from app.services.online_discovery.repository import OnlineDiscoveryRepository
from app.services.online_discovery.search_agent import SearchAgent
from app.services.online_discovery.search_provider_factory import build_search_provider


load_dotenv()

router = APIRouter(prefix="/online-courses", tags=["online-courses"])


class DiscoverSchoolRequest(BaseModel):
    school_name: str
    use_ai: bool = False
    persist: bool = True
    max_pages: int = Field(default=40, ge=5, le=120)
    max_depth: int = Field(default=2, ge=0, le=4)


def build_engine(
    use_ai: bool = False,
    max_pages: int = 40,
    max_depth: int = 2,
) -> OnlineCourseDiscoveryEngine:
    openai_api_key = os.getenv("OPENAI_API_KEY")

    search_provider = build_search_provider()
    search_agent = SearchAgent(provider=search_provider)

    llm_client = None
    if use_ai:
        if not openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
        llm_client = OpenAIJsonClient(api_key=openai_api_key)

    crawler = Crawler()
    classifier = PageClassifier(llm_client=llm_client)
    extractor = CourseExtractor(llm_client=llm_client)
    eligibility = EligibilityJudge(llm_client=llm_client)
    price_resolver = PriceResolver(
        search_agent=search_agent,
        crawler=crawler,
        llm_client=llm_client,
    )
    fact_merger = FactMerger()

    return OnlineCourseDiscoveryEngine(
        search_agent=search_agent,
        crawler=crawler,
        classifier=classifier,
        extractor=extractor,
        eligibility_judge=eligibility,
        price_resolver=price_resolver,
        fact_merger=fact_merger,
        max_pages_per_school=max_pages,
        max_link_depth=max_depth,
    )


@router.post("/discover-school")
async def discover_school(payload: DiscoverSchoolRequest):
    try:
        engine = build_engine(
            use_ai=payload.use_ai,
            max_pages=payload.max_pages,
            max_depth=payload.max_depth,
        )
        result = await engine.discover_school(payload.school_name)
        run_id = None

        if payload.persist:
            repository = OnlineDiscoveryRepository()
            run_id = repository.save_result(
                result=result,
                use_ai=payload.use_ai,
                max_pages=payload.max_pages,
                max_depth=payload.max_depth,
            )

        return {
            "run_id": run_id,
            "school_name": result.school_name,
            "program_pages": result.program_pages,
            "courses": result.courses,
            "missing_tasks": result.missing_tasks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
