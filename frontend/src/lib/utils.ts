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

/** Model outputs attack probability; show confidence in the predicted class. */
export function formatDetectionConfidence(
  isAttack: boolean | null | undefined,
  attackProbability: number | null | undefined,
) {
  const p = Number(attackProbability);
  if (!Number.isFinite(p)) return "0.0%";
  const frac = p > 1 ? p / 100 : p;
  const confidence = isAttack ? frac : 1 - frac;
  return `${(Math.max(0, Math.min(1, confidence)) * 100).toFixed(1)}%`;
}

export function formatMs(value: number | null | undefined) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.0ms";
  return n < 1 ? `${(n * 1000).toFixed(0)}µs` : `${n.toFixed(1)}ms`;
}
