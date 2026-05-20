import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.routes.online_courses import build_engine  # noqa: E402
from app.services.online_discovery.repository import OnlineDiscoveryRepository  # noqa: E402


load_dotenv(ROOT / ".env")


def get_target_schools(limit: int, school: Optional[str] = None) -> list[str]:
    if school:
        return [school]

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing.")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select school_name
                from public.transfer_course_search
                where school_name is not null
                group by school_name
                order by count(*) desc, school_name
                limit %s
                """,
                (limit,),
            )
            return [row[0] for row in cur.fetchall()]


async def run_batch(args: argparse.Namespace) -> None:
    provider = os.getenv("SEARCH_PROVIDER", "google").strip().lower()

    if provider == "google" and (
        not os.getenv("GOOGLE_SEARCH_API_KEY") or not os.getenv("GOOGLE_SEARCH_CX")
    ):
        raise RuntimeError(
            "Google search is selected. Add SEARCH_PROVIDER=google, "
            "GOOGLE_SEARCH_API_KEY, and GOOGLE_SEARCH_CX to .env."
        )

    if provider == "tavily" and not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError(
            "Tavily search is selected. Add SEARCH_PROVIDER=tavily and TAVILY_API_KEY to .env."
        )

    schools = get_target_schools(limit=args.limit, school=args.school)
    repository = OnlineDiscoveryRepository()

    print(f"Running discovery for {len(schools)} school(s).", flush=True)

    for index, school_name in enumerate(schools, start=1):
        print(f"[{index}/{len(schools)}] {school_name}", flush=True)

        try:
            engine = build_engine(
                use_ai=False,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
            )
            result = await engine.discover_school(school_name)

            run_id = None
            if args.persist:
                run_id = repository.save_result(
                    result=result,
                    use_ai=False,
                    max_pages=args.max_pages,
                    max_depth=args.max_depth,
                )

            print(
                "  run_id={run_id} program_pages={pages} courses={courses} missing_tasks={tasks}".format(
                    run_id=run_id or "not_persisted",
                    pages=len(result.program_pages),
                    courses=len(result.courses),
                    tasks=len(result.missing_tasks),
                ),
                flush=True,
            )
        except Exception as exc:
            print(f"  failed: {exc}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local-rule online non-degree credit course discovery."
    )
    parser.add_argument("--school", help="Run one school only.")
    parser.add_argument("--limit", type=int, default=10, help="Top N schools from transfer_course_search.")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    args.persist = not args.no_persist
    return args


def main() -> None:
    asyncio.run(run_batch(parse_args()))


if __name__ == "__main__":
    main()
