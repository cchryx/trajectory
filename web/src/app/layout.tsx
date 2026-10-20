import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trajectory",
  description:
    "Find the internships that fit you. Get the courses that launch you there.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <header className="border-b border-line bg-surface">
          <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
            <Link href="/" className="text-lg font-extrabold tracking-tight">
              Traj<span className="text-accent">ectory</span>
            </Link>
            <Link href="/" className="text-sm text-muted hover:text-foreground">
              Jobs
            </Link>
            <Link
              href="/courses"
              className="text-sm text-muted hover:text-foreground"
            >
              Courses
            </Link>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-line px-4 py-6 text-center text-xs text-muted">
          Job data from the{" "}
          <a
            className="underline"
            href="https://github.com/SimplifyJobs/Summer2027-Internships"
          >
            SimplifyJobs internship list
          </a>
          . Every job links to its original posting. Course data from the{" "}
          <a className="underline" href="https://artsci.calendar.utoronto.ca">
            UofT Arts &amp; Science calendar
          </a>
          .
        </footer>
      </body>
    </html>
  );
}
