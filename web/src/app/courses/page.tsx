import { Suspense } from "react";
import { CourseSearch } from "@/components/course-search";

export default function CoursesPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading...</p>}>
      <CourseSearch />
    </Suspense>
  );
}
