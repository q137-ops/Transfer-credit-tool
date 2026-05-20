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

  const onlineByCode = new Map<string, OnlineCourse>();
  for (const course of onlineCourses) {
    for (const code of extractNormalizedCourseCodes(course.course_code)) {
      if (!onlineByCode.has(code)) {
        onlineByCode.set(code, course);
      }
    }
  }

  const mergedCourses: MergedCourse[] = transferCourses.map((transfer) => {
    const online =
      extractNormalizedCourseCodes(transfer.source_course_code)
        .map((code) => onlineByCode.get(code) ?? null)
        .find(Boolean) ?? null;

    return {
      transfer,
      online,
      status: online
        ? "verified_by_osu_equivalency_and_online"
        : "verified_by_osu_equivalency",
    };
  });

  async function fetchTransferCourses() {
    let request = supabase
      .from("transfer_course_search")
      .select(
        "id, school_name, source_course_code, source_course_title, target_course_code, target_course_title, effective_date, is_online, estimated_price, confidence_level"
      )
      .limit(100);

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

    const { data, error } = await request;
    if (error) {
      throw error;
    }

    setTransferCourses(data ?? []);
  }

  async function fetchOnlineCourses() {
    const terms = [school, query].map((value) => value.trim()).filter(Boolean);
    const q = terms.length ? terms.join(" ") : "online credit course";

    const { data, error } = await supabase.rpc(
      "search_online_course_discovery",
      {
        q,
        max_results: 100,
      }
    );

    if (error) {
      throw error;
    }

    setOnlineCourses((data ?? []) as OnlineCourse[]);
  }

  async function fetchCourses() {
    setLoading(true);
    setErrorMessage(null);

    try {
      await Promise.all([fetchTransferCourses(), fetchOnlineCourses()]);
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
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">
                Courses
              </h2>
              <p className="text-sm text-slate-500">
                Showing {mergedCourses.length} OSU-verified results
              </p>
            </div>
          </div>

          <div className="grid gap-3">
            {mergedCourses.map(({ transfer, online, status }) => (
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
                      {transfer.effective_date || "Unknown"}
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

            {!loading && mergedCourses.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
                No OSU-verified course results.
              </div>
            )}
          </div>
        </section>

      </section>
    </main>
  );
}
