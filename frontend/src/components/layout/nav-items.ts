import {
  LayoutDashboard,
  LineChart,
  Sparkles,
  Users,
  User,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
}

/** Five primary destinations (docs/UI-UX-DESIGN.md §5). */
export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/insights", label: "Insights", Icon: LineChart },
  { href: "/act", label: "Act", Icon: Sparkles },
  { href: "/community", label: "Community", Icon: Users },
  { href: "/profile", label: "Profile", Icon: User },
];
