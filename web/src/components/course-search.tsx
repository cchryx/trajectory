"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { type Course, getFilters, type School, searchCourses } from "@/lib/api";

export function CourseSearch() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const campusParam = params.get("campus") ?? "";
  const [draft, setDraft] = useState(q);
  const [schools, setSchools] = useState<School[]>([]);
  const [results, setResults] = useState<Course[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getFilters()
      .then((f) => setSchools(f.schools))
      .catch(() => setSchools([]));
  }, []);

  // The chosen campus, or the first one we have courses for.
  const campuses = schools.flatMap((s) =>
    s.campuses.map((c) => ({ ...c, schoolId: s.id, schoolName: s.name })),
  );
  const current =
    campuses.find((c) => c.id === campusParam) ??
    campuses.find((c) => c.courses > 0) ??
    campuses[0];
  const campusId = current?.id ?? "";
  const schoolId = current?.schoolId ?? "";

  useEffect(() => {
    setDraft(q);
    if (q.trim().length < 2 || !campusId) {
      setResults(null);
      return;
    }
    let live = true;
    setError("");
    searchCourses(q, schoolId, campusId)
      .then((r) => live && setResults(r.results))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [q, schoolId, campusId]);

  function go(nextQ: string, nextCampus: string) {
    const p = new URLSearchParams();
    if (nextQ) p.set("q", nextQ);
    if (nextCampus) p.set("campus", nextCampus);
    router.push(`/courses?${p}`);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    go(draft.trim(), current?.id ?? "");
  }

  return (
    <div className="grid gap-6">
      <section className="grid gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Find the courses that get you there.
        </h1>
        <p className="max-w-2xl text-muted">
          Describe what you want to learn in plain words, or type a course code.
        </p>
      </section>

      {schools.length > 0 && (
        <section
          aria-label="Choose a school and campus"
          className="grid gap-3 sm:grid-cols-2"
        >
          {schools.map((s) => (
            <div
              key={s.id}
              className="grid gap-2 rounded-lg border border-line bg-surface p-4"
            >
              <h2 className="font-bold">{s.name}</h2>
              <div className="flex flex-wrap gap-2">
                {s.campuses.map((c) => {
                  const active = c.id === current?.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => go(q, c.id)}
                      aria-pressed={active}
                      className={`rounded-md border px-3 py-1.5 text-left text-sm ${
                        active
                          ? "border-accent bg-accent-soft text-accent"
                          : "border-line hover:border-accent"
                      }`}
                    >
                      <span className="font-semibold">{c.name}</span>
                      <span className="block text-xs text-muted">
                        {c.calendar ? `${c.calendar} · ` : ""}
                        {c.courses} courses
                      </span>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-muted">More campuses coming soon.</p>
            </div>
          ))}
        </section>
      )}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="e.g. robots and autonomous systems, or CSC 207"
          aria-label="Search courses"
          className="flex-1 rounded-md border border-line bg-surface p-3"
        />
        <button
          type="submit"
          className="rounded-md bg-accent px-5 font-semibold text-surface"
        >
          Search
        </button>
      </form>
      {current && (
        <p className="-mt-3 text-sm text-muted">
          Searching {current.schoolName}, {current.name} campus.
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {results && results.length === 0 && (
        <p className="text-muted">No courses found. Try other words.</p>
      )}
      {results && results.length > 0 && (
        <ul className="grid gap-3">
          {results.map((c) => (
            <li
              key={c.id}
              className="rounded-lg border border-line bg-surface p-4"
            >
              <Link
                href={`/courses/${encodeURIComponent(c.id)}`}
                className="font-semibold text-accent underline"
              >
                {c.code}: {c.title}
              </Link>
              <p className="mt-1 line-clamp-2 text-sm text-muted">
                {c.description}
              </p>
              {c.skills && c.skills.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                  {c.skills.map((s) => (
                    <span
                      key={s}
                      className="rounded bg-accent-soft px-2 py-0.5 font-mono text-accent"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
