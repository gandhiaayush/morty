import { statusColor } from "@/lib/utils";

interface BadgeProps {
  status: string;
  className?: string;
}

export default function Badge({ status, className = "" }: BadgeProps) {
  return (
    <span className={`badge ${statusColor(status)} ${className}`}>
      {status}
    </span>
  );
}
