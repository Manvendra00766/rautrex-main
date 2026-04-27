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
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  cachedToken = session?.access_token ?? null;

  // Listen for auth changes to update cached token
  supabase.auth.onAuthStateChange((_event, session) => {
    cachedToken = session?.access_token ?? null;
  });
};

if (typeof window !== 'undefined') {
  initToken();
}

// Request interceptor to attach the token
api.interceptors.request.use(async (config) => {
  // If we don't have a token, try one last time to get it
  if (!cachedToken && typeof window !== 'undefined') {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    cachedToken = session?.access_token ?? null;
  }

  if (cachedToken) {
    config.headers.Authorization = `Bearer ${cachedToken}`;
  }
  
  return config;
}, (error) => {
  return Promise.reject(error);
});

export async function getAuthHeaders() {
  if (!cachedToken && typeof window !== 'undefined') {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    cachedToken = session?.access_token ?? null;
  }
  return {
    'Content-Type': 'application/json',
    ...(cachedToken ? { 'Authorization': `Bearer ${cachedToken}` } : {}),
  };
}

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  if (!cachedToken && typeof window !== 'undefined') {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    cachedToken = session?.access_token ?? null;
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(cachedToken ? { 'Authorization': `Bearer ${cachedToken}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed with status code ${response.status}`);
  }

  return response.json();
}

// Response interceptor to handle 401s
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.warn("Unauthorized request detected. Session might be expired.");
      // You could trigger a logout or token refresh here
    }
    return Promise.reject(error);
  }
);

export default api;