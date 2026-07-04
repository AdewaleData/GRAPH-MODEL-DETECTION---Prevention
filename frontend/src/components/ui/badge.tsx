import { cn } from "@/lib/utils";

const variants = {
  default: "bg-primary/15 text-primary border-primary/30",
  secondary: "bg-secondary/15 text-secondary border-secondary/30",
  danger: "bg-danger/15 text-danger border-danger/30",
  success: "bg-success/15 text-success border-success/30",
  warn: "bg-warn/15 text-warn border-warn/30",
  muted: "bg-panel text-muted border-border",
};

export function Badge({
  children,
  variant = "default",
  className,
  pulse,
}: {
  children: React.ReactNode;
  variant?: keyof typeof variants;
  className?: string;
  pulse?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        pulse && "animate-pulse-soft",
        className,
      )}
    >
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
