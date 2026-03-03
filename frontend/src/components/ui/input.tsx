import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-[60px] w-full rounded-xl border border-white/[0.08] bg-transparent px-5 text-base text-slate-100 shadow-sm outline-none transition-colors placeholder:text-slate-400 focus-visible:border-emerald-400/40 focus-visible:ring-0 focus-visible:shadow-[0_0_20px_rgba(0,230,118,0.26)]",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
