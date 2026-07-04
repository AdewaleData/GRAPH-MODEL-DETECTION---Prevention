import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number | null | undefined) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.0%";
  // Accept either fraction (0.72) or percent (72)
  const frac = n > 1 ? n / 100 : n;
  return `${Math.max(0, frac * 100).toFixed(1)}%`;
}

export function formatMs(value: number | null | undefined) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.0ms";
  return n < 1 ? `${(n * 1000).toFixed(0)}µs` : `${n.toFixed(1)}ms`;
}
