"use client";

/** Geometric mark: shield + graph nodes. Brand colors from tailwind theme. */
export function LogoMark({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="hg-edge" x1="8" y1="4" x2="32" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22d3ee" />
          <stop offset="1" stopColor="#a78bfa" />
        </linearGradient>
        <linearGradient id="hg-face" x1="20" y1="6" x2="20" y2="34" gradientUnits="userSpaceOnUse">
          <stop stopColor="#06b6d4" stopOpacity="0.22" />
          <stop offset="1" stopColor="#8b5cf6" stopOpacity="0.06" />
        </linearGradient>
      </defs>
      <path
        d="M20 3.5 33 9v11.5c0 8.2-5.4 14.8-13 16.5C12.4 35.3 7 28.7 7 20.5V9l13-5.5Z"
        fill="url(#hg-face)"
        stroke="url(#hg-edge)"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
      <path
        d="M20 14v8M15.5 21.5 20 18l4.5 3.5"
        stroke="#22d3ee"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <circle cx="20" cy="13" r="2.25" fill="#22d3ee" />
      <circle cx="14.5" cy="24" r="1.75" fill="#a78bfa" />
      <circle cx="25.5" cy="24" r="1.75" fill="#a78bfa" />
      <path d="M20 15.2 14.8 22.5M20 15.2 25.2 22.5" stroke="#64748b" strokeWidth="0.85" opacity="0.55" />
    </svg>
  );
}

export function Logo({
  compact = false,
  className = "",
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="relative flex shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-gradient-to-br from-primary/10 to-secondary/5 p-1.5 shadow-glow">
        <LogoMark className="h-9 w-9" />
      </div>
      {!compact && (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-tight text-white">Halal Graph</p>
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-secondary/90">
            Threat Intel
          </p>
        </div>
      )}
    </div>
  );
}
