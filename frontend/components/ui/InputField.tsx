import React from "react";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  containerClassName?: string;
}

export const InputField = React.forwardRef<HTMLInputElement, InputFieldProps>(
  ({ label, error, className, containerClassName, ...props }, ref) => {
    return (
      <div className={cn("flex flex-col gap-1.5", containerClassName)}>
        <Label className="text-[12px] font-semibold text-text-secondary">{label}</Label>
        <Input 
          ref={ref}
          className={cn("bg-surface border-border text-[14px] text-text-primary h-10 shadow-sm", className)} 
          {...props} 
        />
        {error && <span className="text-[10px] text-negative">{error}</span>}
      </div>
    );
  }
);
InputField.displayName = "InputField";
