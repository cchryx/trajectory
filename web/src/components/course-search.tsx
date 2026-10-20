"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { type Course, searchCourses } from "@/lib/api";

export function CourseSearch() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const [draft, setDraft] = useState(q);
  const [results, setResults] = useState<Course[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setDraft(q);
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    let live = true;
    setError("");
    searchCourses(q)
      .then((r) => live && setResults(r.results))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [q]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    router.push(`/courses?q=${encodeURIComponent(draft.trim())}`);
  }

  return (
    <div className="grid gap-6">
      <section className="grid gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Find the courses that get you there.
        </h1>
        <p className="max-w-2xl text-muted">
          Describe what you want to learn in plain words, or type a course code.
          Starting with UofT Arts &amp; Science (CSC, MAT, STA).
        </p>
      </section>
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
