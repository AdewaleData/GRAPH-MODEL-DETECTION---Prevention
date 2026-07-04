"use client";

import { Bell, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/auth-store";
import { useRealtimeStore } from "@/store/realtime-store";
import { useRouter } from "next/navigation";

export function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  const router = useRouter();
  const email = useAuthStore((s) => s.email);
  const logout = useAuthStore((s) => s.logout);
  const alerts = useRealtimeStore((s) => s.alerts);
  const unacked = alerts.filter((a) => !a.acknowledged).length;

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface/50 px-6 backdrop-blur-md">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="relative" onClick={() => router.push("/alerts")}>
          <Bell className="h-4 w-4" />
          {unacked > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white">
              {unacked > 9 ? "9+" : unacked}
            </span>
          )}
        </Button>
        <Badge variant="secondary" className="hidden sm:inline-flex">
          <User className="mr-1 h-3 w-3" />
          {email?.split("@")[0] ?? "User"}
        </Badge>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            logout();
            router.push("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
