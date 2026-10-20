"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { Select } from "@/components/select";
import { type Course, getFilters, type School, searchCourses } from "@/lib/api";

const PARAMS = ["q", "campus", "faculty", "breadth", "year"] as const;
type Param = (typeof PARAMS)[number];

export function CourseSearch() {
  const router = useRouter();
  const params = useSearchParams();
  const get = (k: Param) => params.get(k) ?? "";
  const q = get("q");
  const faculty = get("faculty");
  const breadth = get("breadth");
  const year = get("year");

  const [draft, setDraft] = useState(q);
  const [schools, setSchools] = useState<School[]>([]);
  const [results, setResults] = useState<Course[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getFilters()
      .then((f) => setSchools(f.schools))
      .catch(() => setSchools([]));
  }, []);

  // The chosen campus, or the first one with courses.
  const campuses = schools.flatMap((s) =>
    s.campuses.map((c) => ({ ...c, schoolId: s.id, schoolName: s.name })),
  );
  const current =
    campuses.find((c) => c.id === get("campus")) ??
    campuses.find((c) => c.courses > 0) ??
    campuses[0];
  const campusId = current?.id ?? "";
  const schoolId = current?.schoolId ?? "";
  const facultyNames = new Map(
    campuses.flatMap((c) => c.faculties.map((f) => [f.id, f.name])),
  );

  useEffect(() => {
    setDraft(q);
    const browsing = !q && (breadth || faculty || year);
    if ((q.trim().length < 2 && !browsing) || !campusId) {
      setResults(null);
      return;
    }
    let live = true;
    setError("");
    searchCourses({
      q,
      school: schoolId,
      campus: campusId,
      faculty,
      breadth,
      year,
    })
      .then((r) => live && setResults(r.results))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [q, schoolId, campusId, faculty, breadth, year]);

  // Change some URL values. Choosing a new campus clears its faculty and breadth.
  function go(changes: Partial<Record<Param, string>>) {
    const next: Record<Param, string> = {
      q,
      campus: campusId,
      faculty,
      breadth,
      year,
      ...changes,
    };
    if (changes.campus && changes.campus !== campusId) {
      next.faculty = changes.faculty ?? "";
      next.breadth = changes.breadth ?? "";
    }
    const p = new URLSearchParams();
    for (const k of PARAMS) if (next[k]) p.set(k, next[k]);
    router.push(`/courses?${p}`);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    go({ q: draft.trim() });
  }

  return (
    <div className="grid gap-6">
      <section className="grid gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Find the courses that get you there.
        </h1>
        <p className="max-w-2xl text-muted">
          Describe what you want to learn in plain words, or type a course code.
          To see every course that counts for a breadth requirement, pick it
          below and leave the search box empty.
        </p>
      </section>

      {schools.map((s) => (
        <section
          key={s.id}
          aria-label={s.name}
          className="grid gap-4 rounded-lg border border-line bg-surface p-4"
        >
          <h2 className="font-bold">{s.name}</h2>

          <div className="grid gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              Campus
            </span>
            <div className="flex flex-wrap gap-2">
              {s.campuses.map((c) => {
                const active = c.id === campusId;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => go({ campus: c.id })}
                    aria-pressed={active}
                    className={`rounded-md border px-3 py-1.5 text-left text-sm ${
                      active
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-line hover:border-accent"
                    }`}
                  >
                    <span className="font-semibold">{c.name}</span>
                    <span className="block text-xs text-muted">
                      {c.courses.toLocaleString()} course
                      {c.courses === 1 ? "" : "s"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {current && current.schoolId === s.id && (
            <div className="grid gap-4 sm:grid-cols-3">
              <Select
                label="Faculty"
                value={faculty}
                onChange={(v) => go({ faculty: v })}
                anyLabel="All faculties"
                options={current.faculties.map((f) => [
                  f.id,
                  `${f.name} (${f.courses})`,
                ])}
              />
              <Select
                label="Breadth requirement"
                value={breadth}
                onChange={(v) => go({ breadth: v })}
                anyLabel="Any"
                options={current.breadth.map((b) => [
                  b.name,
                  `${b.name} (${b.courses})`,
                ])}
              />
              <Select
                label="Year"
                value={year}
                onChange={(v) => go({ year: v })}
                anyLabel="Any"
                options={["1", "2", "3", "4"].map((y) => [y, `Year ${y}`])}
              />
            </div>
          )}
        </section>
      ))}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="e.g. quantum physics, organic chemistry, or CSC 207"
          aria-label="Search courses"
          className="min-w-0 flex-1 rounded-md border border-line bg-surface p-3"
        />
        <button
          type="submit"
          className="rounded-md bg-accent px-5 font-semibold text-surface"
        >
          Search
        </button>
      </form>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {results && results.length === 0 && (
        <p className="text-muted">
          No courses found. Try other words or fewer filters.
        </p>
      )}
      {results && results.length > 0 && (
        <section className="grid gap-3">
          <p className="text-sm text-muted">
            {results.length} course{results.length === 1 ? "" : "s"}
            {current ? ` at ${current.schoolName}, ${current.name}` : ""}
            {breadth ? ` that count for ${breadth}` : ""}.
          </p>
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
                <p className="mt-0.5 text-xs text-muted">
                  {c.faculty_id ? facultyNames.get(c.faculty_id) : ""}
                  {c.year_level ? ` · Year ${c.year_level}` : ""}
                </p>
                <p className="mt-1 line-clamp-2 text-sm text-muted">
                  {c.description}
                </p>
                {((c.skills?.length ?? 0) > 0 ||
                  (c.breadth?.length ?? 0) > 0) && (
                  <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                    {c.breadth?.map((b) => (
                      <span
                        key={b}
                        className="rounded border border-dashed border-gold px-2 py-0.5 text-gold"
                      >
                        Breadth: {b}
                      </span>
                    ))}
                    {c.skills?.map((s) => (
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
        </section>
      )}
    </div>
  );
}
