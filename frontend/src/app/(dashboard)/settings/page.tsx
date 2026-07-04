"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";
import { API_BASE_URL } from "@/lib/config";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const email = useAuthStore((s) => s.email);
  const role = useAuthStore((s) => s.role);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();

  return (
    <>
      <Header title="Settings" subtitle="Account and connection preferences" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Your signed-in profile</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between border-b border-border pb-2">
              <span className="text-muted">Email</span>
              <span className="text-white">{email}</span>
            </div>
            <div className="flex justify-between border-b border-border pb-2">
              <span className="text-muted">Role</span>
              <span className="capitalize text-secondary">{role}</span>
            </div>
            <Button
              variant="danger"
              className="mt-4"
              onClick={() => {
                logout();
                router.push("/login");
              }}
            >
              Sign out
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>Where this dashboard sends requests</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-sm text-primary">{API_BASE_URL}</p>
            <p className="mt-2 text-xs text-muted">
              To point at another server, update the URL in the project config file.
            </p>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
