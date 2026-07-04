import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-white",
        "placeholder:text-muted/60 focus:border-primary/60 focus:outline-none focus:ring-1 focus:ring-primary/40",
        "transition-colors duration-200",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
