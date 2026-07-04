"use client";

export function ConfusionMatrix({
  matrix,
  labels = ["Normal", "Attack"],
}: {
  matrix: readonly (readonly number[])[];
  labels?: [string, string];
}) {
  const max = Math.max(...matrix.flat(), 1);
  const cells = [
    { label: "True Normal", value: matrix[0]?.[0] ?? 0, type: "tn" },
    { label: "False Alert", value: matrix[0]?.[1] ?? 0, type: "fp" },
    { label: "Missed", value: matrix[1]?.[0] ?? 0, type: "fn" },
    { label: "Caught", value: matrix[1]?.[1] ?? 0, type: "tp" },
  ];

  const color = (type: string, v: number) => {
    const intensity = v / max;
    if (type === "tp") return `rgba(16, 185, 129, ${0.2 + intensity * 0.6})`;
    if (type === "tn") return `rgba(6, 182, 212, ${0.15 + intensity * 0.5})`;
    if (type === "fp" || type === "fn") return `rgba(244, 63, 94, ${0.15 + intensity * 0.5})`;
    return "#151d2e";
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between text-xs text-muted px-1">
        <span>Predicted: {labels[0]}</span>
        <span>Predicted: {labels[1]}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {cells.map((c) => (
          <div
            key={c.label}
            className="rounded-lg border border-border p-4 text-center transition-transform duration-200 hover:scale-[1.02]"
            style={{ backgroundColor: color(c.type, c.value) }}
          >
            <p className="text-2xl font-bold text-white tabular-nums">{c.value.toLocaleString()}</p>
            <p className="mt-1 text-xs text-muted">{c.label}</p>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted px-1">
        <span>Actual: {labels[0]}</span>
        <span>Actual: {labels[1]}</span>
      </div>
    </div>
  );
}
