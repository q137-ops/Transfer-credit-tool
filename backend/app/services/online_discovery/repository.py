from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from .models import DiscoveryResult


load_dotenv()


class OnlineDiscoveryRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

        if not self.database_url:
            raise RuntimeError("Missing DATABASE_URL environment variable.")

    def save_result(
        self,
        result: DiscoveryResult,
        use_ai: bool,
        max_pages: int,
        max_depth: int,
    ) -> str:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                run_id = self._create_run(cur, result, use_ai, max_pages, max_depth)
                school_id = self._upsert_school(cur, result.school_name)
                program_page_ids = self._upsert_program_pages(cur, result, run_id, school_id)
                course_ids = self._upsert_courses(cur, result, run_id, school_id, program_page_ids)
                self._insert_missing_tasks(cur, result, run_id, school_id, course_ids)
                self._complete_run(cur, run_id, result)
            conn.commit()

        return run_id

    def _create_run(self, cur, result: DiscoveryResult, use_ai: bool, max_pages: int, max_depth: int) -> str:
        cur.execute(
            """
            insert into public.online_discovery_runs (
              school_name,
              status,
              use_ai,
              max_pages,
              max_depth,
              program_page_count,
              course_count,
              missing_task_count
            )
            values (%s, 'running', %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                result.school_name,
                use_ai,
                max_pages,
                max_depth,
                len(result.program_pages),
                len(result.courses),
                len(result.missing_tasks),
            ),
        )
        return str(cur.fetchone()[0])

    def _complete_run(self, cur, run_id: str, result: DiscoveryResult) -> None:
        cur.execute(
            """
            update public.online_discovery_runs
            set status = 'completed',
                program_page_count = %s,
                course_count = %s,
                missing_task_count = %s,
                completed_at = now()
            where id = %s
            """,
            (len(result.program_pages), len(result.courses), len(result.missing_tasks), run_id),
        )

    def _upsert_school(self, cur, school_name: str) -> str:
        normalized_name = self._normalize_school_name(school_name)

        cur.execute(
            """
            select id
            from public.schools
            where lower(coalesce(normalized_name, name)) = lower(%s)
            limit 1
            """,
            (normalized_name,),
        )
        row = cur.fetchone()

        if row:
            return str(row[0])

        cur.execute(
            """
            insert into public.schools (name, normalized_name)
            values (%s, %s)
            returning id
            """,
            (school_name, normalized_name),
        )
        return str(cur.fetchone()[0])

    def _upsert_program_pages(
        self,
        cur,
        result: DiscoveryResult,
        run_id: str,
        school_id: str,
    ) -> dict[str, str]:
        ids = {}

        for page in result.program_pages:
            facts = self._program_page_flags(page)
            cur.execute(
                """
                insert into public.online_program_pages (
                  school_id,
                  discovery_run_id,
                  url,
                  page_title,
                  page_type,
                  program_type,
                  is_official,
                  is_online,
                  is_credit_bearing,
                  is_non_degree_accessible,
                  requires_degree_admission,
                  confidence,
                  source_snippet,
                  evidence,
                  discovered_by,
                  raw_judgment,
                  last_checked_at,
                  updated_at
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, now(), now()
                )
                on conflict (url) do update set
                  school_id = excluded.school_id,
                  discovery_run_id = excluded.discovery_run_id,
                  page_title = excluded.page_title,
                  page_type = excluded.page_type,
                  program_type = excluded.program_type,
                  is_official = excluded.is_official,
                  is_online = excluded.is_online,
                  is_credit_bearing = excluded.is_credit_bearing,
                  is_non_degree_accessible = excluded.is_non_degree_accessible,
                  requires_degree_admission = excluded.requires_degree_admission,
                  confidence = excluded.confidence,
                  source_snippet = excluded.source_snippet,
                  evidence = excluded.evidence,
                  discovered_by = excluded.discovered_by,
                  raw_judgment = excluded.raw_judgment,
                  last_checked_at = now(),
                  updated_at = now()
                returning id
                """,
                (
                    school_id,
                    run_id,
                    page.get("url"),
                    page.get("title"),
                    page.get("page_type"),
                    page.get("page_type"),
                    True,
                    facts["is_online"],
                    facts["is_academic_credit"],
                    facts["is_non_degree_accessible"],
                    page.get("page_type") == "degree_program_page",
                    page.get("confidence"),
                    page.get("source_snippet") or page.get("evidence"),
                    page.get("evidence"),
                    page.get("discovered_by"),
                    Json(page.get("raw") or {}),
                ),
            )
            ids[page.get("url")] = str(cur.fetchone()[0])

        return ids

    def _upsert_courses(
        self,
        cur,
        result: DiscoveryResult,
        run_id: str,
        school_id: str,
        program_page_ids: dict[str, str],
    ) -> dict[tuple[str | None, str | None], str]:
        ids = {}
        fallback_program_id = next(iter(program_page_ids.values()), None)

        for course in result.courses:
            summary = course.get("facts_summary") or {}
            best = summary.get("best_facts") or {}
            program_page_id = program_page_ids.get(course.get("canonical_course_url")) or fallback_program_id
            price_per_credit = self._number(best, "price_per_credit")
            price_per_course = self._number(best, "price_per_course")

            if price_per_credit is None and "price_candidate" in best:
                price_per_credit = self._number(best, "price_candidate")

            cur.execute(
                """
                insert into public.online_courses (
                  school_id,
                  program_page_id,
                  discovery_run_id,
                  course_code,
                  course_title,
                  credits,
                  canonical_course_url,
                  delivery_mode,
                  final_status,
                  confidence,
                  raw_extraction,
                  is_online,
                  is_academic_credit,
                  is_non_degree_accessible,
                  price_per_credit,
                  price_per_course,
                  registration_url,
                  facts_summary,
                  updated_at
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                on conflict (school_id, course_code, canonical_course_url) do update set
                  program_page_id = excluded.program_page_id,
                  discovery_run_id = excluded.discovery_run_id,
                  course_title = excluded.course_title,
                  credits = excluded.credits,
                  delivery_mode = excluded.delivery_mode,
                  final_status = excluded.final_status,
                  confidence = excluded.confidence,
                  raw_extraction = excluded.raw_extraction,
                  is_online = excluded.is_online,
                  is_academic_credit = excluded.is_academic_credit,
                  is_non_degree_accessible = excluded.is_non_degree_accessible,
                  price_per_credit = excluded.price_per_credit,
                  price_per_course = excluded.price_per_course,
                  registration_url = excluded.registration_url,
                  facts_summary = excluded.facts_summary,
                  updated_at = now()
                returning id
                """,
                (
                    school_id,
                    program_page_id,
                    run_id,
                    course.get("course_code"),
                    course.get("course_title"),
                    course.get("credits"),
                    course.get("canonical_course_url"),
                    course.get("delivery_mode"),
                    summary.get("status"),
                    course.get("confidence"),
                    Json(course.get("raw") or {}),
                    self._truthy(best, "is_online"),
                    self._truthy(best, "is_academic_credit"),
                    self._truthy(best, "is_non_degree_accessible"),
                    price_per_credit,
                    price_per_course,
                    self._text(best, "registration_url"),
                    Json(summary),
                ),
            )
            course_id = str(cur.fetchone()[0])
            ids[(course.get("course_code"), course.get("canonical_course_url"))] = course_id
            self._upsert_best_facts(cur, course_id, run_id, best)

        return ids

    def _upsert_best_facts(self, cur, course_id: str, run_id: str, best: dict[str, Any]) -> None:
        for fact_type, fact in best.items():
            cur.execute(
                """
                insert into public.course_facts (
                  course_id,
                  discovery_run_id,
                  fact_type,
                  value_text,
                  value_number,
                  value_json,
                  source_url,
                  source_title,
                  source_snippet,
                  confidence
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict do nothing
                """,
                (
                    course_id,
                    run_id,
                    fact_type,
                    fact.get("value_text"),
                    fact.get("value_number"),
                    Json(fact.get("value_json") or {}),
                    fact.get("source_url") or "",
                    fact.get("source_title"),
                    fact.get("source_snippet"),
                    fact.get("confidence"),
                ),
            )

    def _insert_missing_tasks(
        self,
        cur,
        result: DiscoveryResult,
        run_id: str,
        school_id: str,
        course_ids: dict[tuple[str | None, str | None], str],
    ) -> None:
        for task in result.missing_tasks:
            course_id = self._find_course_id_for_task(task, course_ids)
            cur.execute(
                """
                insert into public.crawl_tasks (
                  discovery_run_id,
                  school_id,
                  course_id,
                  task_type,
                  query,
                  status,
                  priority,
                  result_json
                )
                values (%s, %s, %s, %s, %s, 'pending', 5, %s)
                """,
                (
                    run_id,
                    school_id,
                    course_id,
                    task.get("task_type"),
                    task.get("query"),
                    Json(task),
                ),
            )

    def _find_course_id_for_task(
        self,
        task: dict[str, Any],
        course_ids: dict[tuple[str | None, str | None], str],
    ) -> str | None:
        course_code = task.get("course_code")

        for (candidate_code, _), course_id in course_ids.items():
            if candidate_code == course_code:
                return course_id

        return None

    def _program_page_flags(self, page: dict[str, Any]) -> dict[str, bool]:
        evidence = json.dumps(page, ensure_ascii=False).lower()

        return {
            "is_online": any(term in evidence for term in ["online", "fully online", "distance"]),
            "is_academic_credit": any(term in evidence for term in ["academic credit", "college credit", "credit hours", "semester credit"]),
            "is_non_degree_accessible": any(term in evidence for term in ["non-degree", "nondegree", "visiting student", "guest student", "non-matriculated"]),
        }

    def _normalize_school_name(self, school_name: str) -> str:
        return " ".join(school_name.lower().split())

    def _truthy(self, best: dict[str, Any], fact_type: str) -> bool | None:
        if fact_type not in best:
            return None
        return best[fact_type].get("value_text") == "true"

    def _number(self, best: dict[str, Any], fact_type: str) -> float | None:
        fact = best.get(fact_type)
        if not fact:
            return None
        return fact.get("value_number")

    def _text(self, best: dict[str, Any], fact_type: str) -> str | None:
        fact = best.get(fact_type)
        if not fact:
            return None
        return fact.get("value_text")
