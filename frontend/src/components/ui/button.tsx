import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "emerald";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    const variantClasses = {
      default: "bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-600 hover:to-indigo-700 hover:shadow-indigo-500/40 hover:-translate-y-0.5",
      destructive: "bg-rose-500 text-white shadow-sm hover:bg-rose-600",
      outline: "border border-white/10 bg-transparent hover:bg-white/5 hover:border-white/20 text-slate-200",
      secondary: "bg-white/5 text-slate-100 border border-white/10 hover:bg-white/10 hover:border-white/20 hover:-translate-y-0.5",
      ghost: "hover:bg-white/5 text-slate-300 hover:text-white",
      link: "text-indigo-400 underline-offset-4 hover:underline",
      emerald: "bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/25 hover:from-emerald-600 hover:to-emerald-700 hover:shadow-emerald-500/40 hover:-translate-y-0.5"
    };

    const sizeClasses = {
      default: "h-11 px-5 py-2.5",
      sm: "h-9 rounded-lg px-3 text-xs",
      lg: "h-12 rounded-xl px-8 text-base",
      icon: "h-10 w-10",
    };

    return (
      <Comp
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-semibold ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
