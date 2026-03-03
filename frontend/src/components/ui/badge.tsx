import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide",
  {
    variants: {
      variant: {
        default: "border-white/10 bg-white/[0.03] text-slate-200",
        success:
          "border-emerald-400/25 bg-emerald-400/10 text-emerald-200 shadow-[inset_0_0_0_1px_rgba(52,211,153,0.12)]",
        danger:
          "animate-pulse border-red-400/30 bg-[rgba(239,68,68,0.20)] text-red-200 shadow-[0_0_18px_rgba(239,68,68,0.18)]",
        warning:
          "border-amber-300/25 bg-amber-300/10 text-amber-100 shadow-[inset_0_0_0_1px_rgba(251,191,36,0.10)]",
        wordpress:
          "border-sky-400/25 bg-sky-400/10 text-sky-100 shadow-[0_0_18px_rgba(56,189,248,0.10)]",
        wix:
          "border-slate-300/15 bg-white/[0.04] text-slate-100 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.06)]",
        shopify:
          "border-emerald-400/25 bg-emerald-400/10 text-emerald-100 shadow-[0_0_18px_rgba(0,230,118,0.10)]",
        squarespace:
          "border-emerald-400/20 bg-emerald-400/10 text-emerald-100 shadow-[0_0_18px_rgba(0,230,118,0.10)]",
        custom:
          "border-white/10 bg-white/[0.02] text-slate-300",
        insta_missing:
          "border-[rgba(245,158,11,0.4)] bg-[linear-gradient(45deg,rgba(245,158,11,0.2),rgba(0,230,118,0.12))] text-[#fbbf24]",
        expiring_soon:
          "border-red-400/40 bg-red-500/15 text-red-100 shadow-[0_0_18px_rgba(239,68,68,0.12)]",
        legacy_brand:
          "border-amber-400/40 bg-amber-500/15 text-amber-100 shadow-[0_0_18px_rgba(245,158,11,0.12)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
