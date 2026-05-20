"use client";

import { useState } from "react";
import { Scissors, Plus, Edit2, Trash2, Check, X, ToggleLeft, ToggleRight } from "lucide-react";
import Header from "@/components/layout/Header";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import { useServices, useCreateService, useUpdateService, useDeleteService } from "@/hooks/useServices";
import { formatCurrency } from "@/lib/utils";
import type { Service } from "@/lib/types";

interface ServiceRowProps {
  service: Service;
  onEdit: (s: Service) => void;
  onToggle: (s: Service) => void;
  onDelete: (s: Service) => void;
  isDeleting: boolean;
}

function ServiceRow({ service: s, onEdit, onToggle, onDelete, isDeleting }: ServiceRowProps) {
  return (
    <div className={`group flex items-center gap-4 px-4 py-3 border-b border-zinc-800 last:border-0 ${!s.active ? "opacity-50" : ""}`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-zinc-100">{s.name}</span>
          {!s.active && (
            <span className="badge badge-gray">inactive</span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="mono text-xs text-zinc-500">{s.duration_min} min</span>
          <span className="mono text-xs text-emerald-400">{formatCurrency(s.price)}</span>
        </div>
      </div>

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onToggle(s)}
          title={s.active ? "Deactivate" : "Activate"}
          className="p-1.5 rounded text-zinc-500 hover:text-amber-400 hover:bg-zinc-800 transition-colors"
        >
          {s.active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
        </button>
        <button
          onClick={() => onEdit(s)}
          className="p-1.5 rounded text-zinc-500 hover:text-violet-400 hover:bg-zinc-800 transition-colors"
        >
          <Edit2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onDelete(s)}
          disabled={isDeleting}
          className="p-1.5 rounded text-zinc-500 hover:text-red-400 hover:bg-zinc-800 disabled:opacity-40 transition-colors"
        >
          {isDeleting ? <Spinner className="w-3.5 h-3.5" /> : <Trash2 className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}

interface ServiceFormProps {
  initial?: Partial<Service>;
  onSubmit: (data: { name: string; duration_min: number; price: number }) => void;
  onCancel: () => void;
  isPending: boolean;
  submitLabel: string;
}

function ServiceForm({ initial, onSubmit, onCancel, isPending, submitLabel }: ServiceFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [duration, setDuration] = useState(String(initial?.duration_min ?? 60));
  const [price, setPrice] = useState(String(initial?.price ?? 0));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, duration_min: parseInt(duration), price: parseFloat(price) });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-zinc-400 mb-1">Service Name</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Gel Manicure"
          className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-violet-500 focus:outline-none"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Duration (min)</label>
          <input
            required
            type="number"
            min={15}
            step={15}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 mono focus:border-violet-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Price ($)</label>
          <input
            required
            type="number"
            min={0}
            step={0.01}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 mono focus:border-violet-500 focus:outline-none"
          />
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold rounded-md transition-colors"
        >
          {isPending && <Spinner className="w-3 h-3" />}
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

export default function ServicesPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Service | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const { data: services, isLoading } = useServices();
  const create = useCreateService();
  const update = useUpdateService();
  const del = useDeleteService();

  const handleCreate = (data: { name: string; duration_min: number; price: number }) => {
    create.mutate(data, { onSuccess: () => setCreateOpen(false) });
  };

  const handleUpdate = (data: { name: string; duration_min: number; price: number }) => {
    if (!editTarget) return;
    update.mutate({ id: editTarget.id, payload: data }, { onSuccess: () => setEditTarget(null) });
  };

  const handleToggle = (s: Service) => {
    update.mutate({ id: s.id, payload: { active: !s.active } });
  };

  const handleDelete = (s: Service) => {
    if (!confirm(`Remove "${s.name}"? This cannot be undone.`)) return;
    setDeletingId(s.id);
    del.mutate(s.id, { onSettled: () => setDeletingId(null) });
  };

  const active = services?.filter((s) => s.active) ?? [];
  const inactive = services?.filter((s) => !s.active) ?? [];

  return (
    <>
      <Header
        title="Services"
        subtitle={`${active.length} active · ${inactive.length} inactive`}
        action={{ label: "Add Service", onClick: () => setCreateOpen(true) }}
      />

      <div className="flex-1 p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner className="w-5 h-5" />
          </div>
        ) : !services?.length ? (
          <EmptyState
            icon={Scissors}
            title="No services yet"
            description="Add your nail salon services to start booking appointments."
            action={
              <button
                onClick={() => setCreateOpen(true)}
                className="flex items-center gap-1.5 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold rounded-md transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Service
              </button>
            }
          />
        ) : (
          <div className="max-w-xl bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            {/* Active */}
            {active.map((s) => (
              <ServiceRow
                key={s.id}
                service={s}
                onEdit={setEditTarget}
                onToggle={handleToggle}
                onDelete={handleDelete}
                isDeleting={deletingId === s.id}
              />
            ))}
            {/* Inactive */}
            {inactive.map((s) => (
              <ServiceRow
                key={s.id}
                service={s}
                onEdit={setEditTarget}
                onToggle={handleToggle}
                onDelete={handleDelete}
                isDeleting={deletingId === s.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add Service" width="sm">
        <ServiceForm
          onSubmit={handleCreate}
          onCancel={() => setCreateOpen(false)}
          isPending={create.isPending}
          submitLabel="Create Service"
        />
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Edit Service" width="sm">
        <ServiceForm
          initial={editTarget ?? undefined}
          onSubmit={handleUpdate}
          onCancel={() => setEditTarget(null)}
          isPending={update.isPending}
          submitLabel="Save Changes"
        />
      </Modal>
    </>
  );
}
