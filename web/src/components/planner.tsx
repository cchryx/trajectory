"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CoursePicker } from "@/components/course-picker";
import { Select } from "@/components/select";
import { type Block, WeekGrid } from "@/components/week-grid";
import { getFilters, getPlannerCourses } from "@/lib/api";
import {
  checkCourse,
  chosenSection,
  decodePlan,
  emptyPlan,
  encodePlan,
  isFullYear,
  MAX_TERM_CREDITS,
  meetingIn,
  type Plan,
  type Planned,
  type PlannerCourse,
  pickSection,
  SLOT_NAMES,
  type Slot,
  schoolYear,
  sectionLabel,
  termCredits,
  termKey,
} from "@/lib/plan";

// The school year that is running now: Oct 2026 is in 2026-2027.
function currentStart() {
  const now = new Date();
  return now.getMonth() >= 6 ? now.getFullYear() : now.getFullYear() - 1;
}

export function Planner() {
  const params = useSearchParams();
  const [plan, setPlanState] = useState<Plan | null>(null);
  const [campuses, setCampuses] = useState<[string, string][]>([]);
  const [courses, setCourses] = useState(new Map<string, PlannerCourse>());
  const [timetableYear, setTimetableYear] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Read the plan from the link once, when the page opens.
  // biome-ignore lint/correctness/useExhaustiveDependencies: only on first load
  useEffect(() => {
    setPlanState(
      decodePlan(params.get("p")) ?? emptyPlan("uoft-stg", currentStart()),
    );
  }, []);

  useEffect(() => {
    getFilters()
      .then((f) =>
        setCampuses(
          f.schools.flatMap((s) =>
            s.campuses.map(
              (c) => [c.id, `${s.name}, ${c.name}`] as [string, string],
            ),
          ),
        ),
      )
      .catch(() => setCampuses([]));
  }, []);

  // Every change goes into the link, so the address bar always holds the plan.
  const setPlan = useCallback((update: (p: Plan) => Plan) => {
    setPlanState((old) => {
      if (!old) return old;
      const next = update(old);
      window.history.replaceState(null, "", `/planner?p=${encodePlan(next)}`);
      return next;
    });
  }, []);

  // Load details for any course in the plan we have not seen yet.
  const codes = useMemo(() => {
    if (!plan) return [];
    const all = [
      ...plan.taken,
      ...Object.values(plan.terms).flatMap((l) => l.map((p) => p.code)),
    ];
    return [...new Set(all)];
  }, [plan]);

  useEffect(() => {
    const todo = codes.filter((c) => !courses.has(c));
    if (!todo.length) return;
    let live = true;
    getPlannerCourses(todo.map((c) => `uoft:${c}`))
      .then((r) => {
        if (!live) return;
        setTimetableYear(r.timetable_year);
        setCourses((old) => {
          const next = new Map(old);
          for (const c of r.courses) next.set(c.code, c);
          return next;
        });
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [codes, courses]);

  // Pick a lecture section for newly added courses in the year with a real timetable.
  useEffect(() => {
    if (!plan || !timetableYear) return;
    const year = Number(timetableYear.slice(0, 4));
    const todo: { slot: Slot; code: string; section: string }[] = [];
    for (const slot of ["Y", "F", "S"] as Slot[]) {
      for (const p of plan.terms[termKey(year, slot)] ?? []) {
        const course = courses.get(p.code);
        if (p.section !== undefined || !course) continue;
        const section = pickSection(plan, courses, course, year, slot);
        todo.push({ slot, code: p.code, section: section ?? "" });
      }
    }
    if (!todo.length) return;
    setPlan((old) => {
      const terms = { ...old.terms };
      for (const t of todo) {
        const key = termKey(year, t.slot);
        terms[key] = (terms[key] ?? []).map((p) =>
          p.code === t.code && p.section === undefined
            ? { ...p, section: t.section }
            : p,
        );
      }
      return { ...old, terms };
    });
  }, [plan, courses, timetableYear, setPlan]);

  if (!plan) return <p className="text-muted">Loading...</p>;

  const years = Array.from({ length: plan.years }, (_, i) => plan.start + i);

  function add(year: number, slot: Slot, code: string) {
    const target: Slot = isFullYear(code) ? "Y" : slot === "Y" ? "F" : slot;
    setPlan((p) => {
      const key = termKey(year, target);
      const list = p.terms[key] ?? [];
      if (list.some((x) => x.code === code)) return p;
      return { ...p, terms: { ...p.terms, [key]: [...list, { code }] } };
    });
  }

  function remove(year: number, slot: Slot, code: string) {
    setPlan((p) => {
      const key = termKey(year, slot);
      const list = (p.terms[key] ?? []).filter((x) => x.code !== code);
      const terms = { ...p.terms, [key]: list };
      if (!list.length) delete terms[key];
      return { ...p, terms };
    });
  }

  function setSection(year: number, slot: Slot, code: string, section: string) {
    setPlan((p) => {
      const key = termKey(year, slot);
      return {
        ...p,
        terms: {
          ...p.terms,
          [key]: (p.terms[key] ?? []).map((x) =>
            x.code === code ? { ...x, section } : x,
          ),
        },
      };
    });
  }

  const credits = (code: string) =>
    courses.get(code)?.credits ?? (isFullYear(code) ? 1 : 0.5);
  const takenCredits = plan.taken.reduce((n, c) => n + credits(c), 0);
  const plannedCredits = Object.values(plan.terms)
    .flat()
    .reduce((n, p) => n + credits(p.code), 0);
  const warningCount = years.reduce(
    (n, y) =>
      n +
      (["Y", "F", "S"] as Slot[]).reduce(
        (m, s) =>
          m +
          (plan.terms[termKey(y, s)] ?? []).reduce(
            (k, p) =>
              k + checkCourse(plan, courses, timetableYear, y, s, p).length,
            0,
          ),
        0,
      ),
    0,
  );

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="grid gap-6">
      <section className="grid gap-2">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Plan your courses.
        </h1>
        <p className="max-w-2xl text-muted">
          Add the courses you have taken, then plan each year. Trajectory checks
          prerequisites, which term each course runs in, time clashes and your
          course load. Your plan is saved in this page&apos;s link, so share the
          link to share the plan.
        </p>
      </section>

      <section className="grid gap-4 rounded-lg border border-line bg-surface p-4 sm:grid-cols-3">
        <Select
          label="Campus"
          value={plan.campus}
          onChange={(v) => setPlan((p) => ({ ...p, campus: v }))}
          options={
            campuses.length
              ? campuses
              : [["uoft-stg", "University of Toronto, St. George"]]
          }
        />
        <Select
          label="First school year to plan"
          value={String(plan.start)}
          onChange={(v) => setPlan((p) => ({ ...p, start: Number(v) }))}
          options={[-1, 0, 1].map((d) => {
            const y = currentStart() + d;
            return [String(y), schoolYear(y)];
          })}
        />
        <Select
          label="Years to plan"
          value={String(plan.years)}
          onChange={(v) => setPlan((p) => ({ ...p, years: Number(v) }))}
          options={[1, 2, 3, 4, 5].map((n) => [
            String(n),
            `${n} year${n > 1 ? "s" : ""}`,
          ])}
        />
      </section>

      <section className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-line bg-surface px-4 py-3 text-sm">
        <span>
          <b>{takenCredits.toFixed(1)}</b> credits taken
        </span>
        <span>
          <b>{plannedCredits.toFixed(1)}</b> credits planned
        </span>
        <span className={warningCount ? "text-gold" : "text-accent"}>
          {warningCount
            ? `${warningCount} thing${warningCount > 1 ? "s" : ""} to check`
            : "No problems found"}
        </span>
        <span className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={copyLink}
            className="rounded-md bg-accent px-3 py-1.5 font-semibold text-surface"
          >
            {copied ? "Link copied" : "Copy link to this plan"}
          </button>
          <button
            type="button"
            onClick={() => setPlan((p) => emptyPlan(p.campus, p.start))}
            className="rounded-md border border-line px-3 py-1.5 hover:border-accent"
          >
            Start over
          </button>
        </span>
      </section>

      <section className="grid gap-3 rounded-lg border border-line bg-surface p-4">
        <h2 className="font-bold">Courses you have taken</h2>
        {plan.taken.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {plan.taken.map((code) => (
              <li
                key={code}
                className="flex items-center gap-1 rounded-full border border-line bg-background py-1 pr-1 pl-3 text-sm"
              >
                <span className="font-mono">{code}</span>
                <button
                  type="button"
                  aria-label={`Remove ${code}`}
                  onClick={() =>
                    setPlan((p) => ({
                      ...p,
                      taken: p.taken.filter((c) => c !== code),
                    }))
                  }
                  className="rounded-full px-2 text-muted hover:text-foreground"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="max-w-md">
          <CoursePicker
            campus={plan.campus}
            placeholder="Add a course you have taken"
            onPick={(code) =>
              setPlan((p) =>
                p.taken.includes(code)
                  ? p
                  : { ...p, taken: [...p.taken, code] },
              )
            }
          />
        </div>
      </section>

      {years.map((year) => (
        <YearCard
          key={year}
          year={year}
          plan={plan}
          courses={courses}
          timetableYear={timetableYear}
          onAdd={add}
          onRemove={remove}
          onSection={setSection}
        />
      ))}

      <p className="text-xs text-muted">
        Terms and times come from the UofT Timetable Builder
        {timetableYear ? ` for ${timetableYear}` : ""}. Later years use that
        timetable as a guide, so check the real timetable when it is out. This
        planner does not enrol you. Use ACORN for that.
      </p>
    </div>
  );
}

function YearCard({
  year,
  plan,
  courses,
  timetableYear,
  onAdd,
  onRemove,
  onSection,
}: {
  year: number;
  plan: Plan;
  courses: Map<string, PlannerCourse>;
  timetableYear: string | null;
  onAdd: (year: number, slot: Slot, code: string) => void;
  onRemove: (year: number, slot: Slot, code: string) => void;
  onSection: (year: number, slot: Slot, code: string, section: string) => void;
}) {
  const [showWeek, setShowWeek] = useState(false);
  const real = timetableYear === schoolYear(year);

  const column = (slot: Slot) => {
    const list = plan.terms[termKey(year, slot)] ?? [];
    const load = slot === "Y" ? null : termCredits(plan, courses, year, slot);
    return (
      <div className="grid content-start gap-2">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
            {SLOT_NAMES[slot]}
          </h3>
          {load !== null && (
            <span
              className={`text-xs ${load > MAX_TERM_CREDITS ? "font-semibold text-gold" : "text-muted"}`}
            >
              {load.toFixed(1)} credits
              {load > MAX_TERM_CREDITS ? " · heavy term" : ""}
            </span>
          )}
        </div>
        {list.map((p) => (
          <CourseRow
            key={p.code}
            planned={p}
            course={courses.get(p.code)}
            year={year}
            slot={slot}
            real={real}
            warnings={checkCourse(plan, courses, timetableYear, year, slot, p)}
            onRemove={() => onRemove(year, slot, p.code)}
            onSection={(s) => onSection(year, slot, p.code, s)}
          />
        ))}
        <CoursePicker
          campus={plan.campus}
          placeholder={`Add a ${SLOT_NAMES[slot].toLowerCase()} course`}
          onPick={(code) => onAdd(year, slot, code)}
        />
      </div>
    );
  };

  const blocks = (slot: "F" | "S"): Block[] => {
    const items = meetingIn(plan, year, slot)
      .map(({ p, slot: s }) => ({
        p,
        s,
        section: chosenSection(courses.get(p.code), p, year, s),
      }))
      .filter((x) => x.section);
    return items.map((x) => ({
      code: x.p.code,
      // biome-ignore lint/style/noNonNullAssertion: filtered above
      section: x.section!,
      clash: checkCourse(plan, courses, timetableYear, year, x.s, x.p).some(
        (w) => w.kind === "clash",
      ),
    }));
  };

  return (
    <section className="grid gap-4 rounded-lg border border-line bg-surface p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-bold">{schoolYear(year)}</h2>
        {real ? (
          <button
            type="button"
            onClick={() => setShowWeek(!showWeek)}
            className="text-sm text-accent underline"
          >
            {showWeek ? "Hide weekly timetable" : "Show weekly timetable"}
          </button>
        ) : (
          <span className="text-xs text-muted">
            Timetable not out yet
            {timetableYear ? `. Using ${timetableYear} as a guide.` : "."}
          </span>
        )}
      </div>
      {column("Y")}
      <div className="grid gap-4 md:grid-cols-2">
        {column("F")}
        {column("S")}
      </div>
      {real && showWeek && (
        <div className="grid gap-4 2xl:grid-cols-2">
          {(["F", "S"] as const).map((s) => (
            <div key={s} className="grid gap-1">
              <h3 className="text-sm font-semibold">{SLOT_NAMES[s]}</h3>
              <WeekGrid blocks={blocks(s)} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function CourseRow({
  planned,
  course,
  year,
  slot,
  real,
  warnings,
  onRemove,
  onSection,
}: {
  planned: Planned;
  course: PlannerCourse | undefined;
  year: number;
  slot: Slot;
  real: boolean;
  warnings: ReturnType<typeof checkCourse>;
  onRemove: () => void;
  onSection: (s: string) => void;
}) {
  const sections = (course?.offerings[schoolYear(year)]?.[slot] ?? []).filter(
    (s) => s.type === "LEC",
  );
  return (
    <div
      className={`grid gap-1.5 rounded-lg border bg-background p-3 ${
        warnings.length ? "border-gold/60" : "border-line"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Link
            href={`/courses/${encodeURIComponent(`uoft:${planned.code}`)}`}
            className="font-mono font-semibold text-accent underline"
          >
            {planned.code}
          </Link>{" "}
          <span className="text-sm">{course?.title ?? ""}</span>
          {course?.credits != null && (
            <span className="ml-1 text-xs text-muted">
              · {course.credits} credit
            </span>
          )}
        </div>
        <button
          type="button"
          aria-label={`Remove ${planned.code}`}
          onClick={onRemove}
          className="rounded px-2 text-muted hover:text-foreground"
        >
          ×
        </button>
      </div>
      {real && sections.length > 0 && (
        <label className="grid gap-1 text-xs text-muted">
          Lecture section
          <select
            value={planned.section ?? ""}
            onChange={(e) => onSection(e.target.value)}
            className="h-9 w-full min-w-0 truncate rounded-md border border-line bg-surface px-2 text-sm text-foreground hover:border-accent focus:border-accent focus:outline-none"
          >
            <option value="">No section chosen</option>
            {sections.map((s) => (
              <option key={s.name} value={s.name}>
                {sectionLabel(s)}
              </option>
            ))}
          </select>
        </label>
      )}
      {warnings.map((w) => (
        <p
          key={w.text}
          className={`text-xs ${w.kind === "clash" ? "text-red-500" : "text-gold"}`}
        >
          {w.text}
        </p>
      ))}
    </div>
  );
}
