"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarDays,
  Search,
  Users,
  Scissors,
  BarChart3,
  Phone,
  Activity,
} from "lucide-react";

const nav = [
  { href: "/dashboard",           label: "Today",     icon: CalendarDays },
  { href: "/dashboard/search",    label: "Search",    icon: Search },
  { href: "/dashboard/customers", label: "Customers", icon: Users },
  { href: "/dashboard/services",  label: "Services",  icon: Scissors },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-[220px] bg-zinc-900 border-r border-zinc-800 flex flex-col z-20">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-zinc-800 shrink-0">
        <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
          <Phone className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="font-semibold text-zinc-100 tracking-tight">Morty</span>
        <span className="ml-auto text-[10px] font-medium text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
          ops
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                active
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${active ? "text-violet-400" : ""}`} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-zinc-800">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs text-zinc-500">
            <span className="text-emerald-400 font-medium">Live</span> · tool-server
          </span>
        </div>
      </div>
    </aside>
  );
}
