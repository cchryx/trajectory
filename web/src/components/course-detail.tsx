"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PrereqGraph } from "@/components/prereq-graph";
import {
  type CourseDetail as Detail,
  getCourse,
  type PrereqTree,
} from "@/lib/api";

export function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const courseId = decodeURIComponent(id);
  const [course, setCourse] = useState<Detail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    setCourse(null);
    setError("");
    getCourse(courseId)
      .then((c) => live && setCourse(c))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [courseId]);

  if (error) {
    return (
      <p role="alert" className="text-red-600">
        {error}
      </p>
    );
  }
  if (!course) return <p className="text-muted">Loading...</p>;

  // The requirements, written out from the shared and/or tree. Every item in the list is needed.
  const tree = course.prereq_tree;
  const items =
    tree && typeof tree === "object" && "and" in tree
      ? tree.and
      : tree
        ? [tree]
        : [];

  return (
    <div className="grid gap-6">
      <Link href="/courses" className="text-sm text-accent underline">
        Back to course search
      </Link>
      <section className="grid gap-2">
        {course.school_name && (
          <p className="text-sm font-medium text-accent">
            {course.school_name}
            {course.campus_name ? ` · ${course.campus_name} campus` : ""}
          </p>
        )}
        <p className="font-mono text-sm text-muted">
          {course.code} · year {course.year_level} · {course.credits} credit
          {course.calendar_year ? ` · ${course.calendar_year} calendar` : ""}
        </p>
        <h1 className="text-3xl font-extrabold tracking-tight">
          {course.title}
        </h1>
        <p className="max-w-3xl">{course.description}</p>
        {course.url && (
          <a
            href={course.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-accent underline"
          >
            Official calendar page
          </a>
        )}
      </section>

      <section className="grid gap-3">
        <h2 className="text-xl font-bold">What it needs</h2>
        <PrereqGraph
          rootId={course.id}
          nodes={course.graph.nodes}
          edges={course.graph.edges}
        />
        {items.length > 0 && (
          <div className="grid gap-1 text-sm">
            <p className="font-medium">You need all of these:</p>
            <ol className="grid list-decimal gap-1 pl-5">
              {items.map((item) => (
                <li key={JSON.stringify(item)}>
                  <Requirement node={item} school={course.school_id} top />
                </li>
              ))}
            </ol>
          </div>
        )}
        {course.prereq_text && (
          <p className="text-sm text-muted">
            Calendar wording: {course.prereq_text}
          </p>
        )}
      </section>

      <section className="grid gap-2">
        <h2 className="text-xl font-bold">What it unlocks</h2>
        {course.unlocks.length === 0 ? (
          <p className="text-sm text-muted">
            No loaded course lists it as a prerequisite.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {course.unlocks.map((u) => (
              <li key={u.id}>
                <Link
                  href={`/courses/${encodeURIComponent(u.id)}`}
                  className="inline-block rounded border border-line bg-surface px-3 py-1 text-sm hover:border-accent"
                >
                  <span className="font-semibold">{u.code}</span> {u.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {course.exclusions && (
        <p className="text-sm text-muted">Exclusions: {course.exclusions}</p>
      )}
    </div>
  );
}

// Writes one requirement in plain words, with links to the courses.
function Requirement({
  node,
  school,
  top = false,
}: {
  node: PrereqTree;
  school: string;
  top?: boolean;
}) {
  if (typeof node === "string") {
    return (
      <Link
        href={`/courses/${encodeURIComponent(`${school}:${node}`)}`}
        className="font-mono text-accent underline"
      >
        {node}
      </Link>
    );
  }
  const isOr = "or" in node;
  const parts = isOr ? node.or : node.and;
  const joined = parts.map((p, i) => (
    <span key={JSON.stringify(p)}>
      {i > 0 && (isOr ? (top ? ", " : " or ") : " and ")}
      <Requirement node={p} school={school} />
    </span>
  ));
  if (isOr)
    return (
      <>
        {top ? "One of: " : "("}
        {joined}
        {top ? "" : ")"}
      </>
    );
  return (
    <>
      {top ? "" : "("}
      {joined}
      {top ? "" : ")"}
    </>
  );
}
