"use client";

import { format } from "date-fns";
import { Plus } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function Header({ title, subtitle, action }: HeaderProps) {
  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between px-6 shrink-0">
      <div className="flex flex-col justify-center">
        <h1 className="text-sm font-semibold text-zinc-100 leading-none">{title}</h1>
        {subtitle && (
          <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-3">
        <span className="mono text-zinc-500 hidden sm:block">
          {format(new Date(), "EEE, MMM d")}
        </span>
        {action && (
          <button
            onClick={action.onClick}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold rounded-md transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            {action.label}
          </button>
        )}
      </div>
    </header>
  );
}
