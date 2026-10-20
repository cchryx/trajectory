"use client";

// One styled dropdown, used on every page so they all look the same.
export function Select({
  label,
  value,
  onChange,
  options,
  anyLabel,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
  // Text for the empty choice, like "Any". Leave it out to have no empty choice.
  anyLabel?: string;
}) {
  const active = value !== "";
  return (
    <label className="grid min-w-0 gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </span>
      <span className="relative block">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`peer h-11 w-full min-w-0 cursor-pointer appearance-none truncate rounded-lg border bg-background pr-10 pl-3 text-sm transition-colors hover:border-accent focus:border-accent focus:ring-2 focus:ring-accent/30 focus:outline-none ${
            active
              ? "border-accent/70 text-foreground"
              : "border-line text-muted"
          }`}
        >
          {anyLabel !== undefined && <option value="">{anyLabel}</option>}
          {options.map(([v, name]) => (
            <option key={v} value={v}>
              {name}
            </option>
          ))}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-muted transition-colors peer-hover:text-accent peer-focus:text-accent"
        >
          <path
            d="M5 7.5l5 5 5-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </label>
  );
}
