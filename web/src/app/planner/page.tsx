import { Suspense } from "react";
import { Planner } from "@/components/planner";

export default function PlannerPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading...</p>}>
      <Planner />
    </Suspense>
  );
}
