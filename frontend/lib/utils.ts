import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatError(err: any): string {
  if (!err) return 'An unknown error occurred';
  if (typeof err === 'string') return err;
  
  // Handle browser Event or ErrorEvent instances cleanly to avoid [object Event]
  if (typeof window !== 'undefined' && err instanceof Event) {
    return `Browser ${err.type || 'Event'} error`;
  }

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
  
  if (detail instanceof Error) {
    return detail.message;
  }
  
  if (typeof detail === 'object' && detail !== null) {
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  
  return String(detail);
}
