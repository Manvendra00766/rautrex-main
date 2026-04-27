/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable source maps in production to be safe
  productionBrowserSourceMaps: false,
  
  // Disable transpilePackages for framer-motion as it often triggers source map issues
  transpilePackages: [],

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
