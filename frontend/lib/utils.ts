import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatError(err: any): string {
  if (!err) return 'An unknown error occurred';
  if (typeof err === 'string') return err;
  
  // Extract detail from Axios or fetch-like error structures
  const detail = err?.response?.data?.detail || err?.detail || err?.message || err;
  
  if (Array.isArray(detail)) {
    // Handle Pydantic validation errors: [{type, loc, msg, input}, ...]
    return detail.map((d: any) => {
      if (typeof d === 'string') return d;
      const field = d.loc ? d.loc[d.loc.length - 1] : 'Error';
      return `${field}: ${d.msg}`;
    }).join('; ');
  }
  
  if (typeof detail === 'object' && detail !== null) {
    return JSON.stringify(detail);
  }
  
  return String(detail);
}
