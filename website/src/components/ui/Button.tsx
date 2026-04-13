import { ButtonHTMLAttributes, forwardRef } from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50 disabled:pointer-events-none relative overflow-hidden group",
          {
            "bg-indigo-600 text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-600/30":
              variant === "primary",
            "bg-white hover:bg-zinc-50 text-zinc-900 border border-zinc-200 shadow-sm":
              variant === "secondary",
            "border-2 border-zinc-200 bg-transparent hover:border-zinc-300 hover:bg-zinc-50 text-zinc-900":
              variant === "outline",
            "bg-transparent hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900":
              variant === "ghost",
            "h-9 px-4 text-sm": size === "sm",
            "h-11 px-6 text-base": size === "md",
            "h-14 px-8 text-lg": size === "lg",
          },
          className
        )}
        {...props}
      >
        {variant === "primary" && (
          <span className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out z-0" />
        )}
        <span className="relative z-10 flex items-center gap-2">{props.children}</span>
      </button>
    );
  }
);
Button.displayName = "Button";
