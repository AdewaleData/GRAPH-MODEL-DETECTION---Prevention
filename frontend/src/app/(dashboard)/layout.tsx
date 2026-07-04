"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Logo } from "@/components/brand/logo";
import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <AuthGuard>
      <div className="flex h-[100dvh] flex-col overflow-hidden bg-canvas lg:flex-row">
        {/* Mobile top bar */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface/80 px-4 backdrop-blur-md lg:hidden">
          <button
            type="button"
            aria-label="Open menu"
            className="rounded-lg p-2 text-muted hover:bg-panel hover:text-white"
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <Logo compact />
          <div className="w-9" aria-hidden />
        </div>

        {/* Desktop sidebar */}
        <Sidebar className="hidden lg:flex" />

        {/* Mobile drawer */}
        {mobileNavOpen && (
          <>
            <button
              type="button"
              aria-label="Close menu overlay"
              className="fixed inset-0 z-40 bg-black/60 lg:hidden"
              onClick={() => setMobileNavOpen(false)}
            />
            <Sidebar
              mobile
              className="fixed inset-y-0 left-0 z-50 shadow-2xl lg:hidden"
              onNavigate={() => setMobileNavOpen(false)}
            />
          </>
        )}

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </AuthGuard>
  );
}
