import { cn } from "./Card";

interface StatusBadgeProps {
  status: string;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({ status, className, showIcon = true }: StatusBadgeProps) {
  const norm = (status || "").toUpperCase();
  
  let colorClass = "bg-border-subtle/50 text-text-secondary border-border-subtle";
  let label = status || "UNKNOWN";
  let symbol = "○";

  if (norm.includes("AVAILABLE") && !norm.includes("UN")) {
    colorClass = "bg-[#10B981]/15 text-status-available border-[#10B981]/30";
    label = "AVAILABLE";
    symbol = "●";
  } else if (norm.includes("PARTIAL")) {
    colorClass = "bg-[#EAB308]/15 text-status-partial border-[#EAB308]/30";
    label = "PARTIAL";
    symbol = "▲";
  } else if (norm.includes("UNAVAILABLE") || norm.includes("INVALID")) {
    colorClass = "bg-[#EF4444]/15 text-status-unavailable border-[#EF4444]/30";
    label = "UNAVAILABLE";
    symbol = "✕";
  } else if (norm.includes("CONFIGURED")) {
    colorClass = "bg-sky-500/15 text-sky-400 border-sky-500/30";
    label = "CONFIGURED";
    symbol = "◐";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono font-bold rounded-sm tracking-wider uppercase border",
        colorClass,
        className
      )}
      role="status"
    >
      {showIcon && <span className="text-[11px] leading-none" aria-hidden="true">{symbol}</span>}
      <span>{label}</span>
    </span>
  );
}
