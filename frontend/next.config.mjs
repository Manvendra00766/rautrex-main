import { fileURLToPath } from 'node:url'

const tracingRoot = fileURLToPath(new URL('./', import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: tracingRoot,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // Disable source maps in production to be safe
  productionBrowserSourceMaps: false,
  
  // Disable transpilePackages for framer-motion as it often triggers source map issues
  transpilePackages: [],

  async headers() {
    const isProd = process.env.NODE_ENV === 'production';
    
    const headers = [
      {
        key: 'X-Frame-Options',
        value: 'DENY',
      },
      {
        key: 'X-Content-Type-Options',
        value: 'nosniff',
      },
      {
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
      },
      {
        key: 'Permissions-Policy',
        value: 'camera=(), microphone=(), geolocation=()',
      },
    ];

    if (isProd) {
      headers.push({
        key: 'Content-Security-Policy',
        value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.supabase.co; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.supabase.co; connect-src 'self' https://*.supabase.co wss://*.supabase.co http://localhost:8000 ws://localhost:3000; font-src 'self' data:; frame-src 'self'; object-src 'none';",
      });
    }

    return [
      {
        source: '/(.*)',
        headers,
      },
    ];
  },

  webpack: (config, { dev, isServer }) => {
    // Aggressively ignore source map warnings from libraries in all environments
    config.ignoreWarnings = [
      { message: /Failed to parse source map/ },
      { module: /framer-motion/ },
      { module: /node_modules/ }
    ];

    return config;
  },
};

export default nextConfig;
