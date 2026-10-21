"use client";

import { useEffect, useId, useRef, useState } from "react";
import { type Course, searchCourses } from "@/lib/api";
import { schoolOf } from "@/lib/plan";

// Type a course code or a topic, then pick a course to add.
export function CoursePicker({
  campus,
  onPick,
  placeholder = "Add a course",
}: {
  campus: string;
  onPick: (code: string) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Course[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    let live = true;
    const timer = setTimeout(() => {
      searchCourses({ q, school: schoolOf(campus), campus })
        .then((r) => {
          if (!live) return;
          setResults(r.results.slice(0, 8));
          setActive(0);
          setOpen(true);
        })
        .catch(() => live && setResults([]));
    }, 250);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [q, campus]);

  useEffect(() => {
    function close(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function pick(code: string) {
    onPick(code);
    setQ("");
    setResults([]);
    setOpen(false);
  }

  return (
    <div ref={box} className="relative">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        onKeyDown={(e) => {
          if (!open || !results.length) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            pick(results[active].code);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
        placeholder={placeholder}
        aria-label={placeholder}
        aria-expanded={open}
        aria-controls={listId}
        role="combobox"
        className="h-10 w-full rounded-lg border border-dashed border-line bg-background px-3 text-sm placeholder:text-muted hover:border-accent focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
      />
      {open && results.length > 0 && (
        <div
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full min-w-64 overflow-auto rounded-lg border border-line bg-surface py-1 shadow-lg"
        >
          {results.map((c, i) => (
            <div
              key={c.id}
              role="option"
              tabIndex={-1}
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(c.code);
              }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3 py-2 text-sm ${
                i === active ? "bg-accent-soft" : ""
              }`}
            >
              <span className="font-mono font-semibold">{c.code}</span>{" "}
              <span className="text-muted">{c.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
