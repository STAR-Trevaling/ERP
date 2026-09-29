import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "cyan" | "purple";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "border-transparent bg-indigo-500/15 text-indigo-400 border border-indigo-500/30",
    secondary: "border-transparent bg-slate-800 text-slate-300 border border-white/10",
    destructive: "border-transparent bg-rose-500/15 text-rose-400 border border-rose-500/30",
    outline: "text-slate-300 border-white/10",
    success: "border-transparent bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
    warning: "border-transparent bg-amber-500/15 text-amber-400 border border-amber-500/30",
    cyan: "border-transparent bg-cyan-500/15 text-cyan-400 border border-cyan-500/30",
    purple: "border-transparent bg-purple-500/15 text-purple-400 border border-purple-500/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
