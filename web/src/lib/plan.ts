// The course plan: what it holds, how it fits in a link, and the checks on it.
import type { PrereqTree } from "@/lib/api";

export type Slot = "F" | "S" | "Y"; // Fall, Winter, full year
export const SLOTS: Slot[] = ["Y", "F", "S"];
export const SLOT_NAMES: Record<Slot, string> = {
  F: "Fall",
  S: "Winter",
  Y: "Full year",
};

export type Planned = { code: string; section?: string };

export type Plan = {
  v: 1;
  campus: string; // 'uoft-stg'
  start: number; // 2026 means the 2026-2027 school year
  years: number; // how many school years to plan
  taken: string[]; // course codes already done
  terms: Record<string, Planned[]>; // key like "2026F"
};

export type Section = {
  name: string;
  type: string;
  times: { day: number; start: number; end: number }[];
};

export type PlannerCourse = {
  id: string;
  code: string;
  title: string;
  credits: number | null;
  year_level: number | null;
  campus_id: string | null;
  prereq_tree: PrereqTree | null;
  exclusion_codes: string[];
  breadth: string[] | null;
  url: string | null;
  terms_offered: string[] | null;
  offerings: Record<string, Partial<Record<Slot, Section[]>>>;
};

export const MAX_TERM_CREDITS = 2.5; // a normal full load at UofT

export function schoolYear(start: number) {
  return `${start}-${start + 1}`;
}

export function termKey(year: number, slot: Slot) {
  return `${year}${slot}`;
}

// A campus id starts with its school id: "uoft-stg" belongs to "uoft".
export function schoolOf(campus: string) {
  return campus.split("-")[0];
}

export function courseId(campus: string, code: string) {
  return `${schoolOf(campus)}:${code}`;
}

export function emptyPlan(campus: string, start: number): Plan {
  return { v: 1, campus, start, years: 4, taken: [], terms: {} };
}

// Full-year courses at UofT end in Y + campus digit: MAT137Y1, POL200Y5.
export function isFullYear(code: string) {
  return /[A-Z]{3}[A-Z0-9]\d{2}Y\d/.test(code);
}

// ---- The link ----------------------------------------------------------

export function encodePlan(plan: Plan): string {
  const bytes = new TextEncoder().encode(JSON.stringify(plan));
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodePlan(text: string | null): Plan | null {
  if (!text) return null;
  try {
    const bin = atob(text.replace(/-/g, "+").replace(/_/g, "/"));
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    const plan = JSON.parse(new TextDecoder().decode(bytes));
    if (plan?.v !== 1 || typeof plan.start !== "number") return null;
    return {
      v: 1,
      campus: String(plan.campus ?? ""),
      start: plan.start,
      years: Math.min(6, Math.max(1, Number(plan.years) || 4)),
      taken: Array.isArray(plan.taken) ? plan.taken.map(String) : [],
      terms: typeof plan.terms === "object" && plan.terms ? plan.terms : {},
    };
  } catch {
    return null;
  }
}

// ---- Checks ------------------------------------------------------------

export type Warning = {
  kind: "prereq" | "term" | "clash" | "exclusion" | "repeat";
  text: string;
};

// Every course done before a term starts: taken courses, plus courses in earlier terms.
// A full-year course is done at the end of Winter.
export function doneBefore(plan: Plan, year: number, slot: Slot): Set<string> {
  const done = new Set(plan.taken);
  for (let y = plan.start; y <= year; y++) {
    for (const s of SLOTS) {
      const earlier = y < year || (slot === "S" && s === "F");
      if (!earlier) continue;
      for (const p of plan.terms[termKey(y, s)] ?? []) done.add(p.code);
    }
  }
  return done;
}

export function meets(tree: PrereqTree | null, done: Set<string>): boolean {
  if (tree === null) return true;
  if (typeof tree === "string") return done.has(tree);
  if ("and" in tree) return tree.and.every((t) => meets(t, done));
  return tree.or.some((t) => meets(t, done));
}

export function describe(tree: PrereqTree, top = true): string {
  if (typeof tree === "string") return tree;
  if ("and" in tree) {
    const parts = tree.and.map((t) => describe(t, false));
    return top ? parts.join(" and ") : `(${parts.join(" and ")})`;
  }
  const parts = tree.or.map((t) => describe(t, false));
  return top ? `one of ${parts.join(", ")}` : `(${parts.join(" or ")})`;
}

// The requirements still missing, written out.
export function missing(tree: PrereqTree | null, done: Set<string>): string[] {
  if (tree === null || meets(tree, done)) return [];
  const items = typeof tree !== "string" && "and" in tree ? tree.and : [tree];
  return items.filter((t) => !meets(t, done)).map((t) => describe(t));
}

// Which timetable to use for a school year: its own, or the latest one as a guide.
export function offeringFor(
  course: PlannerCourse,
  year: number,
  timetableYear: string | null,
): {
  terms: Partial<Record<Slot, Section[]>>;
  exact: boolean;
  from: string | null;
} {
  const own = course.offerings[schoolYear(year)];
  if (own) return { terms: own, exact: true, from: schoolYear(year) };
  const latest = timetableYear ? course.offerings[timetableYear] : undefined;
  if (latest) return { terms: latest, exact: false, from: timetableYear };
  return { terms: {}, exact: false, from: null };
}

function overlaps(a: Section, b: Section) {
  return a.times.some((x) =>
    b.times.some((y) => x.day === y.day && x.start < y.end && y.start < x.end),
  );
}

export function chosenSection(
  course: PlannerCourse | undefined,
  planned: Planned,
  year: number,
  slot: Slot,
): Section | undefined {
  if (!course || !planned.section) return undefined;
  const sections = course.offerings[schoolYear(year)]?.[slot] ?? [];
  return sections.find((s) => s.name === planned.section);
}

// Courses that meet in a term: its own courses plus the full-year ones.
export function meetingIn(plan: Plan, year: number, slot: "F" | "S") {
  return [
    ...(plan.terms[termKey(year, slot)] ?? []).map((p) => ({ p, slot })),
    ...(plan.terms[termKey(year, "Y")] ?? []).map((p) => ({
      p,
      slot: "Y" as Slot,
    })),
  ];
}

export function termCredits(
  plan: Plan,
  courses: Map<string, PlannerCourse>,
  year: number,
  slot: "F" | "S",
) {
  let total = 0;
  for (const { p, slot: s } of meetingIn(plan, year, slot)) {
    const credits =
      courses.get(p.code)?.credits ?? (isFullYear(p.code) ? 1 : 0.5);
    total += s === "Y" ? credits / 2 : credits;
  }
  return total;
}

// All warnings for one planned course.
export function checkCourse(
  plan: Plan,
  courses: Map<string, PlannerCourse>,
  timetableYear: string | null,
  year: number,
  slot: Slot,
  planned: Planned,
): Warning[] {
  const out: Warning[] = [];
  const course = courses.get(planned.code);
  if (!course) return out;

  const lack = missing(course.prereq_tree, doneBefore(plan, year, slot));
  if (lack.length)
    out.push({ kind: "prereq", text: `Needs ${lack.join("; ")} first.` });

  const { terms, exact, from } = offeringFor(course, year, timetableYear);
  const offered = Object.keys(terms) as Slot[];
  if (from && offered.length && !offered.includes(slot)) {
    const names = offered.map((s) => SLOT_NAMES[s]).join(" or ");
    out.push({
      kind: "term",
      text: `Offered in ${names}${exact ? "" : ` in ${from}`}, not ${SLOT_NAMES[slot]}.`,
    });
  }

  const everywhere = [
    ...plan.taken.map((code) => ({ code, where: "taken" })),
    ...Object.entries(plan.terms).flatMap(([key, list]) =>
      list.map((p) => ({ code: p.code, where: key })),
    ),
  ];
  if (everywhere.filter((e) => e.code === planned.code).length > 1) {
    out.push({
      kind: "repeat",
      text: "This course is in your plan more than once.",
    });
  }
  const clashWith = course.exclusion_codes.filter((x) =>
    everywhere.some((e) => e.code === x),
  );
  if (clashWith.length) {
    out.push({
      kind: "exclusion",
      text: `Can't count with ${clashWith.join(", ")} (exclusion).`,
    });
  }

  // Time clashes, only where the real timetable for that year is known.
  const mine = chosenSection(course, planned, year, slot);
  if (mine) {
    const terms: ("F" | "S")[] = slot === "Y" ? ["F", "S"] : [slot];
    const hits = new Set<string>();
    for (const t of terms) {
      for (const other of meetingIn(plan, year, t)) {
        if (other.p.code === planned.code) continue;
        const theirs = chosenSection(
          courses.get(other.p.code),
          other.p,
          year,
          other.slot,
        );
        if (theirs && overlaps(mine, theirs)) hits.add(other.p.code);
      }
    }
    if (hits.size) {
      out.push({
        kind: "clash",
        text: `Time clash with ${[...hits].join(", ")}.`,
      });
    }
  }
  return out;
}

// A lecture section that fits around the sections already chosen, if there is one.
export function pickSection(
  plan: Plan,
  courses: Map<string, PlannerCourse>,
  course: PlannerCourse,
  year: number,
  slot: Slot,
): string | undefined {
  const sections = (course.offerings[schoolYear(year)]?.[slot] ?? []).filter(
    (s) => s.type === "LEC",
  );
  if (!sections.length) return undefined;
  const terms: ("F" | "S")[] = slot === "Y" ? ["F", "S"] : [slot];
  const taken = terms.flatMap((t) =>
    meetingIn(plan, year, t)
      .map((o) => chosenSection(courses.get(o.p.code), o.p, year, o.slot))
      .filter((s): s is Section => !!s),
  );
  return (
    sections.find((s) => !taken.some((t) => overlaps(s, t))) ?? sections[0]
  ).name;
}

export function minutes(m: number) {
  const h = Math.floor(m / 60);
  const mm = String(m % 60).padStart(2, "0");
  return `${h}:${mm}`;
}

export const DAYS = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function sectionLabel(s: Section) {
  if (!s.times.length) return `${s.name} (no set time)`;
  const times = s.times
    .map((t) => `${DAYS[t.day]} ${minutes(t.start)}-${minutes(t.end)}`)
    .join(", ");
  return `${s.name} · ${times}`;
}
