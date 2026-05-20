"use client";

import { useState } from "react";
import {
  TrendingUp, DollarSign, XCircle, Clock,
  BarChart2, AlertCircle,
} from "lucide-react";
import Header from "@/components/layout/Header";
import Spinner from "@/components/ui/Spinner";
import { useAnalytics } from "@/hooks/useAnalytics";
import { formatCurrency, formatDate } from "@/lib/utils";

const RANGE_OPTIONS = [7, 14, 30, 90] as const;
type Range = (typeof RANGE_OPTIONS)[number];

function StatTile({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl px-5 py-4">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-2xl font-bold text-zinc-100">{value}</p>
      <p className="text-xs text-zinc-500 mt-0.5">{label}</p>
      {sub && <p className="text-[11px] text-zinc-600 mt-1">{sub}</p>}
    </div>
  );
}

function MiniBar({ value, max, label, sub }: { value: number; max: number; label: string; sub: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="mono text-xs text-zinc-500 w-10 text-right shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-violet-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="mono text-xs text-zinc-400 w-6 shrink-0">{sub}</span>
    </div>
  );
}

function BookingChart({ data }: { data: { date: string; count: number; revenue: number }[] }) {
  if (!data.length) return null;
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="space-y-1.5">
      {data.slice(-14).map((d) => (
        <MiniBar
          key={d.date}
          label={formatDate(d.date).split(",")[0]}
          value={d.count}
          max={maxCount}
          sub={String(d.count)}
        />
      ))}
    </div>
  );
}

const HOUR_LABELS = [
  "9a", "10a", "11a", "12p", "1p", "2p", "3p", "4p", "5p",
];

export default function AnalyticsPage() {
  const [range, setRange] = useState<Range>(30);
  const { data, isLoading, isError } = useAnalytics(range);

  const busiestSlots = data?.busiest_slots ?? [];
  const maxSlotCount = Math.max(...busiestSlots.map((s) => s.count ?? 0), 1);

  return (
    <>
      <Header title="Analytics" subtitle={`Last ${range} days`} />

      <div className="flex-1 p-6 space-y-6">
        {/* Range selector */}
        <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded-lg p-1 w-fit">
          {RANGE_OPTIONS.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                range === r
                  ? "bg-violet-600 text-white"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {r}d
            </button>
          ))}
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-24">
            <Spinner className="w-6 h-6" />
          </div>
        )}

        {isError && (
          <div className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 rounded-xl p-5 max-w-md">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-medium text-zinc-200">Analytics unavailable</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                The analytics endpoint is not yet available. Connect the backend to see data here.
              </p>
            </div>
          </div>
        )}

        {data && !isLoading && (
          <>
            {/* KPI tiles */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatTile
                icon={TrendingUp}
                label={`Bookings (${range}d)`}
                value={String(data.total_booked)}
                sub={`avg ${(data.total_booked / range).toFixed(1)}/day`}
                color="bg-violet-600/10 text-violet-400"
              />
              <StatTile
                icon={DollarSign}
                label="Revenue"
                value={formatCurrency(data.total_revenue)}
                sub={`avg ${formatCurrency(data.total_revenue / range)}/day`}
                color="bg-emerald-600/10 text-emerald-400"
              />
              <StatTile
                icon={XCircle}
                label="Cancellation rate"
                value={`${(data.cancellation_rate * 100).toFixed(1)}%`}
                color="bg-red-600/10 text-red-400"
              />
              <StatTile
                icon={Clock}
                label="Avg revenue/booking"
                value={
                  data.total_booked > 0
                    ? formatCurrency(data.total_revenue / data.total_booked)
                    : "—"
                }
                color="bg-blue-600/10 text-blue-400"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Bookings per day chart */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart2 className="w-4 h-4 text-violet-400" />
                  <h3 className="text-sm font-semibold text-zinc-200">Bookings per day</h3>
                </div>
                {data.daily_bookings.length === 0 ? (
                  <p className="text-xs text-zinc-500">No data for this range.</p>
                ) : (
                  <BookingChart data={data.daily_bookings} />
                )}
              </div>

              {/* Busiest time slots */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-zinc-200">Busiest time slots</h3>
                </div>
                {busiestSlots.length === 0 ? (
                  <p className="text-xs text-zinc-500">No data for this range.</p>
                ) : (
                  <div className="space-y-1.5">
                    {busiestSlots.slice(0, 9).map((slot) => (
                      <MiniBar
                        key={slot.hour}
                        label={HOUR_LABELS[slot.hour - 9] ?? `${slot.hour}:00`}
                        value={slot.count}
                        max={maxSlotCount}
                        sub={String(slot.count)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
