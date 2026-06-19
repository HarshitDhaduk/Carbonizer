import type { CategoryBreakdown } from "@/lib/types";
import { StatCard } from "./StatCard";

export function CategoryGrid({
  categories,
}: {
  categories: CategoryBreakdown[];
}) {
  return (
    <section aria-label="Emissions by category">
      <h2 className="mb-2 text-sm font-medium text-text-mid">This period</h2>
      <div className="grid grid-cols-2 gap-2.5">
        {categories.map((c) => (
          <StatCard key={c.category} data={c} />
        ))}
      </div>
    </section>
  );
}
