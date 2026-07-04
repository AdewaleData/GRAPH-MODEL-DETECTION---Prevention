"use client";

import { useWebSockets } from "@/hooks/use-websocket";
import { useAuthStore } from "@/store/auth-store";
import { Toaster } from "sonner";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  useWebSockets(!!token);

  return (
    <>
      {children}
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: "#151d2e",
            border: "1px solid #1e2a3d",
            color: "#fff",
          },
        }}
      />
    </>
  );
}
