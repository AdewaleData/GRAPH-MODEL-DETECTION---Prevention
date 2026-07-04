"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accent = "primary",
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  accent?: "primary" | "secondary" | "danger" | "success";
}) {
  const accentMap = {
    primary: "text-primary border-primary/20",
    secondary: "text-secondary border-secondary/20",
    danger: "text-danger border-danger/20",
    success: "text-success border-success/20",
  };

  return (
    <Card className="group overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted">{title}</p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-white transition-transform duration-300 group-hover:scale-[1.02]">
              {value}
            </p>
            {subtitle && (
              <p
                className={cn(
                  "mt-1 text-xs",
                  trend === "up" && "text-danger",
                  trend === "down" && "text-success",
                  !trend && "text-muted",
                )}
              >
                {subtitle}
              </p>
            )}
          </div>
          <div
            className={cn(
              "rounded-lg border p-2.5 transition-transform duration-300 group-hover:scale-110",
              accentMap[accent],
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
