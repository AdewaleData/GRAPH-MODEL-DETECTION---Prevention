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
  X,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { cn } from "@/lib/utils";
import { useRealtimeStore } from "@/store/realtime-store";

export const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/traffic", label: "Live Traffic", icon: Activity },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/prevention", label: "Prevention", icon: ShieldBan },
  { href: "/graph", label: "Network Graph", icon: Network },
  { href: "/analytics", label: "Model Analytics", icon: BarChart3 },
  { href: "/health", label: "System Health", icon: HeartPulse },
  { href: "/settings", label: "Settings", icon: Settings },
];

type SidebarProps = {
  className?: string;
  mobile?: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ className, mobile = false, onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const connected = useRealtimeStore((s) => s.connected);
  const liveCount = Object.values(connected).filter(Boolean).length;

  return (
    <aside
      className={cn(
        "flex h-full w-64 shrink-0 flex-col border-r border-border bg-surface/95 backdrop-blur-xl",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-4">
        <Logo />
        {mobile && onNavigate && (
          <button
            type="button"
            aria-label="Close menu"
            className="rounded-lg p-2 text-muted hover:bg-panel hover:text-white lg:hidden"
            onClick={onNavigate}
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                active
                  ? "border border-primary/20 bg-primary/10 text-primary shadow-glow"
                  : "border border-transparent text-muted hover:bg-panel hover:text-white",
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
                <span className="ml-auto h-2 w-2 animate-pulse-soft rounded-full bg-secondary" />
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
