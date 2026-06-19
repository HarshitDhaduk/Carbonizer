import { DashboardClient } from "@/components/dashboard/DashboardClient";

// The dashboard is now per-user and client-fetched (auth-guarded), so this route
// is dynamic rather than statically prerendered.
export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return <DashboardClient />;
}
