"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

type TransferCourse = {
  id: string;
  school_name: string | null;
  source_course_code: string | null;
  source_course_title: string | null;
  target_course_code: string | null;
  target_course_title: string | null;
  effective_date: string | null;
  is_online: boolean | null;
  estimated_price: number | null;
  confidence_level: string | null;
};

type OnlineCourse = {
  id: string;
  school_name: string | null;
  course_code: string | null;
  course_title: string | null;
  credits: number | string | null;
  canonical_course_url: string | null;
  delivery_mode: string | null;
  is_online: boolean | null;
  is_academic_credit: boolean | null;
  is_non_degree_accessible: boolean | null;
  price_per_credit: number | string | null;
  price_per_course: number | string | null;
  registration_url: string | null;
  final_status: string | null;
  confidence: number | string | null;
  program_url: string | null;
  rank_score: number | string | null;
};

type MergedCourse = {
  transfer: TransferCourse;
  online: OnlineCourse | null;
  status: "verified_by_osu_equivalency" | "verified_by_osu_equivalency_and_online";
};

const TRANSFER_PAGE_SIZE = 1000;
const ONLINE_PAGE_SIZE = 1000;
const MAX_TRANSFER_RESULTS = 10000;
const MAX_ONLINE_RESULTS_PER_SCHOOL_BATCH = 10000;
const SCHOOL_BATCH_SIZE = 25;

function money(value: number | string | null) {
  if (value === null || value === "") {
    return "Unknown";
  }

  const numberValue = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: numberValue % 1 === 0 ? 0 : 2,
  }).format(numberValue);
}

function numberText(value: number | string | null) {
  if (value === null || value === "") {
    return "Unknown";
  }

  const numberValue = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  return numberValue.toLocaleString("en-US", {
    maximumFractionDigits: 2,
  });
}

// OSU transfer-articulation "effective term" codes are 5 digits: YYYY + term.
// Modern OSU SIS uses 4 digits (1238 = Au 2023, mapping 2=Sp, 4=Su, 8=Au), but
// the transfer-articulation feed in this dataset only uses the legacy 5-digit form.
// Term-digit mapping inferred from data distribution across ~30 years of records:
//   4 -> Autumn  (dominant across all years, standard effective term)
//   2 -> Spring  (only appears 2015+, matches post-2012 semester conversion)
//   3 -> Summer  (only appears 2017+, matches semester-era summer term)
//   1 -> unlabeled (only 4 rows, all year 2014; likely data artifact)
// Unmapped digits fall back to "Term N" so we never mislabel.
const TERM_LABELS: Record<string, string> = {
  "2": "Spring",
  "3": "Summer",
  "4": "Autumn",
};

function formatEffectiveDate(value: string | null) {
  if (!value) {
    return "Unknown";
  }

  const trimmed = value.trim();
  const match = trimmed.match(
    /^(\d{4})(\d)(?:\s+To\s+(Present|(\d{4})(\d)))?\s*$/i
  );

  if (!match) {
    return trimmed;
  }

  const [, startYear, startTerm, tail, endYear, endTerm] = match;
  const start = `${TERM_LABELS[startTerm] ?? `Term ${startTerm}`} ${startYear}`;

  if (!tail) {
    return start;
  }

  if (/^present$/i.test(tail)) {
    return `${start} – Present`;
  }

  const end = `${TERM_LABELS[endTerm!] ?? `Term ${endTerm}`} ${endYear}`;
  return `${start} – ${end}`;
}

function extractNormalizedCourseCodes(value: string | null) {
  if (!value) {
    return [];
  }

  const matches = value.match(/[A-Z]{2,}\s*-?\s*\d{2,4}[A-Z]?/gi) ?? [];
  const codes = matches.length ? matches : [value];

  return Array.from(
    new Set(
      codes
        .map((code) => code.replace(/[^a-z0-9]/gi, "").toUpperCase())
        .filter(Boolean)
    )
  );
}

function normalizeSchoolName(value: string | null) {
  return (value ?? "").trim().replace(/\s+/g, " ").toUpperCase();
}

function courseMatchKey(schoolName: string | null, courseCode: string) {
  return `${normalizeSchoolName(schoolName)}::${courseCode}`;
}

function isUsableOnlineCourse(course: OnlineCourse) {
  return (
    course.is_online !== false &&
    course.is_academic_credit !== false &&
    course.is_non_degree_accessible !== false
  );
}

function searchTerms(value: string) {
  return value
    .replace(/[-_]+/g, " ")
    .split(/\s+/)
    .map((term) => term.trim())
    .filter(Boolean);
}

function safeIlikeTerm(value: string) {
  return value.replace(/[,%()*]/g, "");
}

export default function Home() {
  const [transferCourses, setTransferCourses] = useState<TransferCourse[]>([]);
  const [onlineCourses, setOnlineCourses] = useState<OnlineCourse[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [school, setSchool] = useState("");
  const [target, setTarget] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [transferLimitHit, setTransferLimitHit] = useState(false);
  const [onlineLimitHit, setOnlineLimitHit] = useState(false);
  const [showOnlineMatchesOnly, setShowOnlineMatchesOnly] = useState(false);

  const onlineBySchoolAndCode = new Map<string, OnlineCourse>();
  for (const course of onlineCourses) {
    if (!isUsableOnlineCourse(course)) {
      continue;
    }

    for (const code of extractNormalizedCourseCodes(course.course_code)) {
      const key = courseMatchKey(course.school_name, code);
      if (!onlineBySchoolAndCode.has(key)) {
        onlineBySchoolAndCode.set(key, course);
      }
    }
  }

  const mergedCourses: MergedCourse[] = transferCourses.map((transfer) => {
    const online =
      extractNormalizedCourseCodes(transfer.source_course_code)
        .map((code) =>
          onlineBySchoolAndCode.get(courseMatchKey(transfer.school_name, code)) ??
          null
        )
        .find(Boolean) ?? null;

    return {
      transfer,
      online,
      status: online
        ? "verified_by_osu_equivalency_and_online"
        : "verified_by_osu_equivalency",
    };
  });

  const visibleCourses = showOnlineMatchesOnly
    ? mergedCourses.filter(
        (course) => course.status === "verified_by_osu_equivalency_and_online"
      )
    : mergedCourses;

  function buildTransferRequest(from: number, to: number) {
    let request = supabase
      .from("transfer_course_search")
      .select(
        "id, school_name, source_course_code, source_course_title, target_course_code, target_course_title, effective_date, is_online, estimated_price, confidence_level"
      )
      .order("school_name", { ascending: true, nullsFirst: false })
      .order("source_course_code", { ascending: true, nullsFirst: false })
      .order("target_course_code", { ascending: true, nullsFirst: false })
      .order("id", { ascending: true })
      .range(from, to);

    for (const term of searchTerms(query)) {
      const q = safeIlikeTerm(term);
      if (!q) {
        continue;
      }

      request = request.or(
        `school_name.ilike.%${q}%,source_course_code.ilike.%${q}%,source_course_title.ilike.%${q}%,target_course_code.ilike.%${q}%,target_course_title.ilike.%${q}%`
      );
    }

    if (school.trim()) {
      request = request.ilike("school_name", `%${school.trim()}%`);
    }

    if (target.trim()) {
      request = request.ilike("target_course_code", `%${target.trim()}%`);
    }

    return request;
  }

  async function fetchTransferCourses() {
    const rows: TransferCourse[] = [];
    let hitLimit = false;

    for (
      let from = 0;
      from < MAX_TRANSFER_RESULTS;
      from += TRANSFER_PAGE_SIZE
    ) {
      const to = Math.min(from + TRANSFER_PAGE_SIZE - 1, MAX_TRANSFER_RESULTS - 1);
      const { data, error } = await buildTransferRequest(from, to);

      if (error) {
        throw error;
      }

      const page = data ?? [];
      rows.push(...page);

      if (page.length < TRANSFER_PAGE_SIZE) {
        break;
      }

      if (rows.length >= MAX_TRANSFER_RESULTS) {
        hitLimit = true;
      }
    }

    setTransferLimitHit(hitLimit);
    setTransferCourses(rows);
    return rows;
  }

  async function fetchOnlineCoursesForTransferRows(rows: TransferCourse[]) {
    const schoolNames = Array.from(
      new Set(rows.map((row) => row.school_name).filter(Boolean) as string[])
    );

    if (schoolNames.length === 0) {
      setOnlineLimitHit(false);
      setOnlineCourses([]);
      return;
    }

    const onlineRows: OnlineCourse[] = [];
    let hitLimit = false;

    for (let i = 0; i < schoolNames.length; i += SCHOOL_BATCH_SIZE) {
      const schoolBatch = schoolNames.slice(i, i + SCHOOL_BATCH_SIZE);

      for (
        let from = 0;
        from < MAX_ONLINE_RESULTS_PER_SCHOOL_BATCH;
        from += ONLINE_PAGE_SIZE
      ) {
        const to = Math.min(
          from + ONLINE_PAGE_SIZE - 1,
          MAX_ONLINE_RESULTS_PER_SCHOOL_BATCH - 1
        );

        const { data, error } = await supabase
          .from("online_course_discovery_search")
          .select(
            "id, school_name, course_code, course_title, credits, canonical_course_url, delivery_mode, is_online, is_academic_credit, is_non_degree_accessible, price_per_credit, price_per_course, registration_url, final_status, confidence, program_url"
          )
          .in("school_name", schoolBatch)
          .order("school_name", { ascending: true, nullsFirst: false })
          .order("course_code", { ascending: true, nullsFirst: false })
          .order("course_title", { ascending: true, nullsFirst: false })
          .order("id", { ascending: true })
          .range(from, to);

        if (error) {
          throw error;
        }

        const page = (data ?? []) as OnlineCourse[];
        onlineRows.push(...page);

        if (page.length < ONLINE_PAGE_SIZE) {
          break;
        }

        if (from + ONLINE_PAGE_SIZE >= MAX_ONLINE_RESULTS_PER_SCHOOL_BATCH) {
          hitLimit = true;
        }
      }
    }

    setOnlineLimitHit(hitLimit);
    setOnlineCourses(onlineRows);
  }

  async function fetchCourses() {
    setLoading(true);
    setErrorMessage(null);

    try {
      const rows = await fetchTransferCourses();
      await fetchOnlineCoursesForTransferRows(rows);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Search failed unexpectedly.";
      console.error(error);
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchCourses();
    }, 0);

    return () => window.clearTimeout(timer);
    // The initial load should run once; manual searches use the button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 border-b border-slate-200 pb-6">
          <p className="mb-2 text-sm font-medium text-slate-500">
            Transfer Master
          </p>
          <h1 className="text-3xl font-semibold tracking-normal text-slate-950">
            Course search
          </h1>
        </div>

        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-slate-700">
                General Search
              </label>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. BYU chemistry, ASU math, accounting"
                className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                School
              </label>
              <input
                value={school}
                onChange={(e) => setSchool(e.target.value)}
                placeholder="e.g. Columbus State"
                className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Target OSU Course
              </label>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. CHEM"
                className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
              />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={fetchCourses}
              className="rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              {loading ? "Searching..." : "Search"}
            </button>
            {errorMessage && (
              <p className="text-sm font-medium text-red-600">{errorMessage}</p>
            )}
          </div>
        </div>

        <section>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">
                Courses
              </h2>
              <p className="text-sm text-slate-500">
                Showing {visibleCourses.length} of {mergedCourses.length} OSU-verified results
              </p>
              {(transferLimitHit || onlineLimitHit) && (
                <p className="mt-1 text-sm font-medium text-amber-700">
                  Showing the first available results. Narrow the search if a
                  broad query still reaches the safety limit.
                </p>
              )}
            </div>
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm">
              <input
                type="checkbox"
                checked={showOnlineMatchesOnly}
                onChange={(event) =>
                  setShowOnlineMatchesOnly(event.target.checked)
                }
                className="h-4 w-4 accent-slate-950"
              />
              Online matches only
            </label>
          </div>

          <div className="grid gap-3">
            {visibleCourses.map(({ transfer, online, status }) => (
              <article
                key={transfer.id}
                className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-500">
                      {transfer.school_name || "Unknown School"}
                    </p>
                    <h3 className="mt-1 text-lg font-semibold text-slate-950">
                      {transfer.source_course_code || "N/A"}
                      {transfer.source_course_title &&
                      transfer.source_course_title.toLowerCase().trim() !==
                        "course title not in system"
                        ? ` - ${transfer.source_course_title}`
                        : ""}
                    </h3>
                  </div>
                  <span
                    className={
                      online
                        ? "rounded-md bg-emerald-50 px-2 py-1 text-sm font-medium text-emerald-700"
                        : "rounded-md bg-sky-50 px-2 py-1 text-sm font-medium text-sky-700"
                    }
                  >
                    {status}
                  </span>
                </div>

                <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-slate-500">Transfers To</p>
                    <p className="font-medium text-slate-950">
                      {transfer.target_course_code || "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Credits</p>
                    <p className="font-medium text-slate-950">
                      {online ? numberText(online.credits) : "Unknown"}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Course Price</p>
                    <p className="font-medium text-slate-950">
                      {online ? money(online.price_per_course) : money(transfer.estimated_price)}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Effective Date</p>
                    <p className="font-medium text-slate-950">
                      {formatEffectiveDate(transfer.effective_date)}
                    </p>
                  </div>
                </div>

                {online && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {online.canonical_course_url && (
                      <a
                        href={online.canonical_course_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Course Page
                      </a>
                    )}
                    {online.registration_url && (
                      <a
                        href={online.registration_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Registration
                      </a>
                    )}
                    {online.program_url && (
                      <a
                        href={online.program_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Program Page
                      </a>
                    )}
                  </div>
                )}
              </article>
            ))}

            {!loading && visibleCourses.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
                {showOnlineMatchesOnly
                  ? "No OSU-verified online matches."
                  : "No OSU-verified course results."}
              </div>
            )}
          </div>
        </section>

      </section>
    </main>
  );
}
