import axios from 'axios';
import { createClient } from './supabase';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Cache for the token to avoid excessive getSession calls
let cachedToken: string | null = null;

// Initialize token from session
const initToken = async () => {
  if (typeof window === 'undefined') return;
  
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  cachedToken = session?.access_token ?? null;

  // Listen for auth changes to update cached token
  supabase.auth.onAuthStateChange((event, session) => {
    cachedToken = session?.access_token ?? null;
    if (event === 'TOKEN_REFRESHED') {
      console.log('[API] Token refreshed automatically by Supabase');
    }
  });
};

if (typeof window !== 'undefined') {
  initToken();
}

function isTokenExpired(token: string): boolean {
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return true;
    const payloadJson = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson);
    if (!payload.exp) return false;
    
    // Add 10-second buffer for clock skew / transit time
    const currentTime = Math.floor(Date.now() / 1000);
    return payload.exp < (currentTime + 10);
  } catch (e) {
    return true; // If we can't parse it, treat as expired
  }
}

/**
 * Gets a fresh access token from Supabase session.
 * If the current session is expired, attempts to refresh it.
 * This ensures we don't use a stale or expired token.
 */
async function getFreshToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  
  try {
    const supabase = createClient();
    const { data: { session }, error } = await supabase.auth.getSession();
    
    if (!session) {
      cachedToken = null;
      return null;
    }
    
    if (session.access_token && !isTokenExpired(session.access_token)) {
      cachedToken = session.access_token;
      return session.access_token;
    }

    // Session is expired or close to expiring — attempt refresh
    console.log('[API] Session expired or close to expiring. Attempting refresh...');
    const { data: refreshed, error: refreshError } = await supabase.auth.refreshSession();
    
    if (refreshed?.session?.access_token && !refreshError) {
      cachedToken = refreshed.session.access_token;
      console.log('[API] Session refreshed successfully');
      return refreshed.session.access_token;
    }
    
    console.warn('[API] Session refresh failed:', refreshError?.message);
    return null;
  } catch (err) {
    console.error("[API] Failed to get fresh token:", err);
    return null;
  }
}

/**
 * Forces a session refresh and returns the new token.
 * Used as a recovery mechanism when a 401/403 is received.
 */
export async function forceRefreshToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  try {
    const supabase = createClient();
    const { data, error } = await supabase.auth.refreshSession();

    if (data?.session?.access_token && !error) {
      cachedToken = data.session.access_token;
      console.log('[API] Force refresh successful');
      return data.session.access_token;
    }

    console.warn('[API] Force refresh failed:', error?.message);
    return null;
  } catch (err) {
    console.error('[API] Force refresh error:', err);
    return null;
  }
}

// Request interceptor to attach a fresh token
api.interceptors.request.use(async (config) => {
  const token = await getFreshToken();
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor to handle 401s/403s and refresh session
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If we get a 401 or 403 and haven't retried yet
    if ((error.response?.status === 401 || error.response?.status === 403) && !originalRequest._retry) {
      originalRequest._retry = true;
      
      if (typeof window !== 'undefined') {
        try {
          console.log(`[API] ${error.response.status} detected, attempting session refresh...`);
          const newToken = await forceRefreshToken();
          
          if (newToken) {
            // Retry the original request with the new token
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return api(originalRequest);
          }
        } catch (refreshEx) {
          console.error("[API] Refresh failed:", refreshEx);
        }
        
        // If refresh fails or there's no session, force logout and redirect
        console.warn("[API] Session expired and refresh failed. Redirecting to login...");
        const supabase = createClient();
        await supabase.auth.signOut();
        
        // Prevent redirect loop if already on login page
        if (!window.location.pathname.includes('/auth') && !window.location.pathname.includes('/login')) {
          window.location.href = '/login?expired=true';
        }
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Helper to get auth headers for native fetch calls.
 * Attempts refresh if session is expired, or if forceRefresh is specified.
 */
export async function getAuthHeaders(forceRefresh = false): Promise<Record<string, string>> {
  let token = forceRefresh ? await forceRefreshToken() : await getFreshToken();
  
  // If no token from getSession, try force refresh
  if (!token) {
    token = await forceRefreshToken();
  }

  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
}

/**
 * Wrapper for native fetch with auth, 401/403 retry, and error details.
 * Throws with detailed error info so callers can handle specific cases.
 */
export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;

  const executeFetch = async (token: string | null) => {
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  };

  let token = await getFreshToken();
  let response = await executeFetch(token);

  // Handle 401 or 403 with one-time retry after refresh
  if ((response.status === 401 || response.status === 403) && typeof window !== 'undefined') {
    console.log(`[apiFetch] ${response.status} detected on ${endpoint}, attempting refresh...`);
    const newToken = await forceRefreshToken();
    
    if (newToken) {
      token = newToken;
      // Retry with new token
      response = await executeFetch(token);
    } else {
      // Refresh failed, redirect to login
      console.warn("[apiFetch] Refresh failed, redirecting to login...");
      const supabase = createClient();
      await supabase.auth.signOut();
      if (!window.location.pathname.includes('/auth') && !window.location.pathname.includes('/login')) {
        window.location.href = '/login?expired=true';
      }
      throw new Error("Session expired");
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || `Request failed with status ${response.status}`;
    console.error(`[apiFetch] ${response.status} ${response.statusText} on ${endpoint}:`, errorData);
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * Utility: Fetch with exponential backoff retry.
 * Retries up to `maxRetries` times with exponential delay.
 * Does NOT retry on 401/403 (those are handled inside apiFetch).
 */
export async function apiFetchWithRetry(
  endpoint: string,
  options: RequestInit = {},
  maxRetries: number = 3
) {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await apiFetch(endpoint, options);
    } catch (err: any) {
      lastError = err;
      
      // Don't retry auth failures — apiFetch already handles refresh internally
      if (err.message === 'Session expired') {
        throw err;
      }

      if (attempt < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, attempt), 8000); // 1s, 2s, 4s, max 8s
        console.warn(`[apiFetchWithRetry] Attempt ${attempt + 1}/${maxRetries + 1} failed for ${endpoint}. Retrying in ${delay}ms...`, err.message);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError || new Error(`Failed after ${maxRetries + 1} attempts`);
}

export default api;
