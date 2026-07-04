"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  HeartPulse,
  LayoutDashboard,
  Network,
  Settings,
  ShieldBan,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useRealtimeStore } from "@/store/realtime-store";

const nav = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/traffic", label: "Live Traffic", icon: Activity },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/prevention", label: "Prevention", icon: ShieldBan },
  { href: "/graph", label: "Network Graph", icon: Network },
  { href: "/analytics", label: "Model Analytics", icon: BarChart3 },
  { href: "/health", label: "System Health", icon: HeartPulse },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const connected = useRealtimeStore((s) => s.connected);
  const liveCount = Object.values(connected).filter(Boolean).length;

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-surface/90 backdrop-blur-xl">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/30 bg-primary/10">
          <Shield className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-bold text-white leading-tight">Halal Graph</p>
          <p className="text-[10px] uppercase tracking-widest text-secondary">DDoS Shield</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                active
                  ? "bg-primary/10 text-primary border border-primary/20 shadow-glow"
                  : "text-muted hover:bg-panel hover:text-white border border-transparent",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 transition-transform duration-200 group-hover:scale-110",
                  active && "text-primary",
                )}
              />
              {label}
              {href === "/alerts" && liveCount > 0 && (
                <span className="ml-auto h-2 w-2 rounded-full bg-secondary animate-pulse-soft" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-lg border border-border bg-panel/60 p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted">Live feeds</p>
          <p className="mt-1 text-lg font-semibold text-white">{liveCount}/5</p>
          <p className="text-xs text-secondary">channels connected</p>
        </div>
      </div>
    </aside>
  );
}
