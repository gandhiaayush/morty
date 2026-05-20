"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useCancelAppointment } from "@/hooks/useAppointments";
import Spinner from "@/components/ui/Spinner";

interface CancelButtonProps {
  appointmentId: number;
  onDone?: () => void;
}

export default function CancelButton({ appointmentId, onDone }: CancelButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const cancel = useCancelAppointment();

  const handleClick = () => {
    if (!confirming) { setConfirming(true); return; }
    cancel.mutate({ appointment_id: appointmentId }, { onSuccess: onDone });
    setConfirming(false);
  };

  return (
    <button
      onClick={handleClick}
      onBlur={() => setConfirming(false)}
      disabled={cancel.isPending}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors disabled:opacity-50 ${
        confirming
          ? "bg-red-600 hover:bg-red-500 text-white"
          : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
      }`}
    >
      {cancel.isPending ? (
        <Spinner className="w-3 h-3" />
      ) : (
        <Trash2 className="w-3.5 h-3.5" />
      )}
      {confirming ? "Confirm Cancel" : "Cancel Appt"}
    </button>
  );
}
