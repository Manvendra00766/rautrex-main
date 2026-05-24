import React from "react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, description, icon, className }: SectionHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-1 mb-6", className)}>
      <div className="flex items-center gap-2">
        {icon && <span className="text-accent">{icon}</span>}
        <h2 className="text-[18px] font-semibold text-text-primary tracking-tight">{title}</h2>
      </div>
      {description && (
        <p className="text-[14px] text-text-secondary leading-relaxed">{description}</p>
      )}
    </div>
  );
}
