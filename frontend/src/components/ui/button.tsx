"use client";

import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
        "disabled:pointer-events-none disabled:opacity-50",
        "active:scale-[0.98]",
        variant === "default" && "bg-primary text-canvas hover:bg-primary/90 shadow-glow",
        variant === "secondary" && "bg-secondary/20 text-secondary border border-secondary/30 hover:bg-secondary/30",
        variant === "ghost" && "text-muted hover:bg-panel hover:text-white",
        variant === "danger" && "bg-danger/20 text-danger border border-danger/40 hover:bg-danger/30",
        variant === "outline" && "border border-border text-muted hover:border-primary/50 hover:text-primary",
        size === "sm" && "h-8 px-3 text-xs",
        size === "md" && "h-10 px-4 text-sm",
        size === "lg" && "h-12 px-6 text-base",
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
