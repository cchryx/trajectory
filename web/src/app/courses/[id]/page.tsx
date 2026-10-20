import { Suspense } from "react";
import { CourseDetail } from "@/components/course-detail";

export default function CoursePage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading...</p>}>
      <CourseDetail />
    </Suspense>
  );
}
