"use client";

import { DAYS, minutes, type Section } from "@/lib/plan";

const START = 8 * 60; // 8:00
const END = 22 * 60; // 22:00
const HOUR_PX = 28;
const COLORS = [
  "#0b7a62",
  "#7c3aed",
  "#be185d",
  "#2563eb",
  "#a16207",
  "#0e7490",
  "#b45309",
];

export type Block = { code: string; section: Section; clash: boolean };

// One week, Monday to Friday, with the chosen sections drawn as blocks.
export function WeekGrid({ blocks }: { blocks: Block[] }) {
  const height = ((END - START) / 60) * HOUR_PX;
  const codes = [...new Set(blocks.map((b) => b.code))];
  const hours = Array.from(
    { length: (END - START) / 60 + 1 },
    (_, i) => START / 60 + i,
  );

  return (
    <div className="overflow-x-auto">
      <div
        className="grid min-w-[520px] text-[11px]"
        style={{ gridTemplateColumns: "40px repeat(5, 1fr)" }}
      >
        <div />
        {[1, 2, 3, 4, 5].map((d) => (
          <div key={d} className="pb-1 text-center font-semibold text-muted">
            {DAYS[d]}
          </div>
        ))}
        <div className="relative" style={{ height }}>
          {hours.slice(0, -1).map((h) => (
            <div
              key={h}
              className="absolute right-1 text-muted"
              style={{ top: (h * 60 - START) * (HOUR_PX / 60) - 6 }}
            >
              {h}:00
            </div>
          ))}
        </div>
        {[1, 2, 3, 4, 5].map((day) => (
          <div
            key={day}
            className="relative border-l border-line"
            style={{ height }}
          >
            {hours.slice(0, -1).map((h) => (
              <div
                key={h}
                className="absolute inset-x-0 border-t border-line/60"
                style={{ top: (h * 60 - START) * (HOUR_PX / 60) }}
              />
            ))}
            {blocks.flatMap((b) =>
              b.section.times
                .filter((t) => t.day === day && t.end > START && t.start < END)
                .map((t) => {
                  const color = COLORS[codes.indexOf(b.code) % COLORS.length];
                  return (
                    <div
                      key={`${b.code}-${t.day}-${t.start}`}
                      title={`${b.code} ${b.section.name} ${minutes(t.start)}-${minutes(t.end)}`}
                      className={`absolute inset-x-0.5 overflow-hidden rounded px-1 py-0.5 leading-tight text-white ${
                        b.clash ? "ring-2 ring-red-500" : ""
                      }`}
                      style={{
                        top:
                          (Math.max(t.start, START) - START) * (HOUR_PX / 60),
                        height:
                          (Math.min(t.end, END) - Math.max(t.start, START)) *
                            (HOUR_PX / 60) -
                          2,
                        background: color,
                      }}
                    >
                      <div className="font-semibold">{b.code}</div>
                      <div className="opacity-80">{minutes(t.start)}</div>
                    </div>
                  );
                }),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
