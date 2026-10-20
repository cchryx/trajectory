// Talks to the Trajectory API (FastAPI). Set NEXT_PUBLIC_API_URL when you build.
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export type Job = {
  id: string;
  company: string;
  title: string;
  url: string;
  locations: string[] | null;
  terms: string[] | null;
  category: string | null;
  date_posted: string | null;
  has_description: boolean;
  similarity: number;
  fit: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type CourseRef = {
  id: string;
  code: string;
  title: string;
  year_level?: number | null;
  url?: string | null;
};

export type MissingSkill = {
  skill: string;
  jobs: number;
  courses: CourseRef[];
};

export type MatchResult = {
  resume_skills: string[];
  jobs: Job[];
  common_missing: MissingSkill[];
  took_ms: number;
};

export type Faculty = { id: string; name: string; courses: number };

export type Campus = {
  id: string;
  name: string;
  courses: number;
  faculties: Faculty[];
  breadth: { name: string; courses: number }[];
};

export type School = { id: string; name: string; campuses: Campus[] };

export type Filters = {
  countries: { id: string; name: string }[];
  terms: string[];
  categories: string[];
  schools: School[];
  open_postings: number;
  with_description: number;
};

export type Course = {
  id: string;
  campus_id: string | null;
  faculty_id: string | null;
  breadth: string[] | null;
  code: string;
  title: string;
  description: string | null;
  year_level: number | null;
  credits: number | null;
  url: string | null;
  skills: string[] | null;
  prereq_text: string | null;
  score?: number;
};

export type GraphNode = {
  id: string;
  code: string;
  title: string | null;
  year_level: number | null;
  loaded: boolean;
};
export type GraphEdge = {
  from: string;
  to: string;
  group: number;
  level: number;
};

export type PrereqTree = string | { and: PrereqTree[] } | { or: PrereqTree[] };

export type CourseDetail = Course & {
  prereq_tree: PrereqTree | null;
  school_id: string;
  school_name: string | null;
  campus_name: string | null;
  faculty_name: string | null;
  exclusions: string | null;
  recommended: string | null;
  calendar_year: string | null;
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
  unlocks: CourseRef[];
};

async function read<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Something went wrong (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function getFilters(): Promise<Filters> {
  return read(await fetch(`${API_URL}/filters`));
}

export async function matchResume(form: FormData): Promise<MatchResult> {
  return read(await fetch(`${API_URL}/match`, { method: "POST", body: form }));
}

export type CourseQuery = {
  q: string;
  school: string;
  campus?: string;
  faculty?: string;
  breadth?: string;
  year?: string;
};

export async function searchCourses(
  query: CourseQuery,
): Promise<{ results: Course[] }> {
  const params = new URLSearchParams({ limit: query.q ? "15" : "100" });
  for (const [k, v] of Object.entries(query)) if (v) params.set(k, v);
  return read(await fetch(`${API_URL}/courses/search?${params}`));
}

export async function getCourse(id: string): Promise<CourseDetail> {
  return read(await fetch(`${API_URL}/courses/${encodeURIComponent(id)}`));
}

export async function getPlannerCourses(ids: string[]): Promise<{
  courses: import("@/lib/plan").PlannerCourse[];
  timetable_year: string | null;
}> {
  const params = new URLSearchParams({ ids: ids.join(",") });
  return read(await fetch(`${API_URL}/planner/courses?${params}`));
}
