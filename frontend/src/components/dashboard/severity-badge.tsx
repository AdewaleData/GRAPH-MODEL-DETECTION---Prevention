import { Badge } from "@/components/ui/badge";

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  const variant =
    s === "critical" || s === "high"
      ? "danger"
      : s === "medium"
        ? "warn"
        : s === "low"
          ? "success"
          : "muted";
  return (
    <Badge variant={variant} pulse={s === "critical"}>
      {severity}
    </Badge>
  );
}
