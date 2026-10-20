"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import {
  type Filters,
  getFilters,
  type Job,
  type MatchResult,
  matchResume,
} from "@/lib/api";

const MAX_BYTES = 2 * 1024 * 1024;

export function JobFinder() {
  const [filters, setFilters] = useState<Filters | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pasted, setPasted] = useState("");
  const [usePaste, setUsePaste] = useState(false);
  const [country, setCountry] = useState("");
  const [term, setTerm] = useState("");
  const [category, setCategory] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MatchResult | null>(null);

  useEffect(() => {
    getFilters()
      .then(setFilters)
      .catch(() => setFilters(null));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const form = new FormData();
    if (usePaste) {
      if (pasted.trim().length < 50) {
        setError("Paste more of your resume (at least a few lines).");
        return;
      }
      form.set("text", pasted);
    } else {
      if (!file) {
        setError("Choose your resume PDF first.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setError("The PDF is bigger than 2 MB.");
        return;
      }
      form.set("file", file);
    }
    if (country) form.set("country", country);
    if (term) form.set("term", term);
    if (category) form.set("category", category);

    setBusy(true);
    try {
      setResult(await matchResume(form));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8">
      <section className="grid gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Find the internships that fit you.
        </h1>
        <p className="max-w-2xl text-muted">
          Upload your resume. Trajectory ranks{" "}
          {filters ? filters.open_postings.toLocaleString() : "open"}{" "}
          internships by fit and shows the skills you are missing for each one.
          Then it finds courses that teach those skills.
        </p>
      </section>

      <form
        onSubmit={onSubmit}
        className="grid gap-4 rounded-lg border border-line bg-surface p-5"
      >
        {usePaste ? (
          <label className="grid gap-1 text-sm font-medium">
            Resume text
            <textarea
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              rows={8}
              className="rounded-md border border-line bg-background p-3 font-normal"
              placeholder="Paste your resume here"
            />
          </label>
        ) : (
          <label className="grid gap-1 text-sm font-medium">
            Resume (PDF, up to 2 MB)
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="rounded-md border border-dashed border-line bg-background p-3 font-normal file:mr-3 file:rounded file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:text-accent"
            />
          </label>
        )}
        <button
          type="button"
          onClick={() => setUsePaste(!usePaste)}
          className="justify-self-start text-sm text-accent underline"
        >
          {usePaste ? "Upload a PDF instead" : "Paste text instead"}
        </button>

        <div className="grid gap-3 sm:grid-cols-3">
          <Select
            label="Location"
            value={country}
            onChange={setCountry}
            options={(filters?.countries ?? []).map((c) => [c.id, c.name])}
          />
          <Select
            label="Term"
            value={term}
            onChange={setTerm}
            options={(filters?.terms ?? []).map((t) => [t, t])}
          />
          <Select
            label="Role type"
            value={category}
            onChange={setCategory}
            options={(filters?.categories ?? []).map((c) => [c, c])}
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-accent px-5 py-2 font-semibold text-surface disabled:opacity-60"
          >
            {busy ? "Matching..." : "Find my matches"}
          </button>
          <p className="text-xs text-muted">
            Your resume is used for this search and then deleted. It is never
            saved.
          </p>
        </div>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
      </form>

      {result && <Results result={result} />}
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="grid gap-1 text-sm font-medium">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-line bg-background p-2 font-normal"
      >
        <option value="">Any</option>
        {options.map(([v, name]) => (
          <option key={v} value={v}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

function Results({ result }: { result: MatchResult }) {
  if (result.jobs.length === 0) {
    return (
      <p className="text-muted">
        No open internships match these filters. Try fewer filters.
      </p>
    );
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <section className="grid content-start gap-3">
        <h2 className="text-xl font-bold">Your top {result.jobs.length}</h2>
        {result.resume_skills.length > 0 && (
          <p className="text-sm text-muted">
            Skills found in your resume: {result.resume_skills.join(", ")}.
          </p>
        )}
        {result.jobs.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </section>
      <aside className="grid content-start gap-3">
        <h2 className="text-xl font-bold">Skills to learn</h2>
        <p className="text-sm text-muted">
          Missing most often across your top matches.
        </p>
        {result.common_missing.length === 0 && (
          <p className="text-sm text-muted">
            None. Your resume covers the listed skills.
          </p>
        )}
        {result.common_missing.map((m) => (
          <div
            key={m.skill}
            className="rounded-lg border border-line bg-surface p-3"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-semibold">{m.skill}</span>
              <span className="text-xs text-muted">
                in {m.jobs} job{m.jobs === 1 ? "" : "s"}
              </span>
            </div>
            {m.courses.length > 0 ? (
              <ul className="mt-2 grid gap-1 text-sm">
                {m.courses.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`/courses/${encodeURIComponent(c.id)}`}
                      className="text-accent underline"
                    >
                      {c.code}
                    </Link>{" "}
                    {c.title}
                  </li>
                ))}
              </ul>
            ) : (
              <Link
                href={`/courses?q=${encodeURIComponent(m.skill)}`}
                className="mt-2 block text-sm text-accent underline"
              >
                Search courses
              </Link>
            )}
          </div>
        ))}
      </aside>
    </div>
  );
}

function JobCard({ job }: { job: Job }) {
  const pct = Math.round(job.fit * 100);
  return (
    <article className="grid gap-2 rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{job.title}</h3>
          <p className="text-sm text-muted">
            {job.company}
            {job.locations?.length ? ` · ${job.locations.join(", ")}` : ""}
            {job.terms?.length ? ` · ${job.terms.join(", ")}` : ""}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-accent-soft px-3 py-1 text-sm font-bold text-accent">
          {pct}% fit
        </span>
      </div>
      <div className="h-1.5 rounded bg-line">
        <div
          className="h-full rounded bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-1.5 text-xs">
        {job.matched_skills.map((s) => (
          <span
            key={s}
            className="rounded bg-accent-soft px-2 py-0.5 font-mono text-accent"
          >
            {s}
          </span>
        ))}
        {job.missing_skills.map((s) => (
          <span
            key={s}
            className="rounded border border-dashed border-gold px-2 py-0.5 font-mono text-gold"
          >
            missing: {s}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-accent underline"
        >
          View posting
        </a>
        {!job.has_description && (
          <span className="text-xs text-muted">
            Matched on title and skills only. No public description.
          </span>
        )}
      </div>
    </article>
  );
}
