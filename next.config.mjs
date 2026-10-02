/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  experimental: { instrumentationHook: true },
  images: { formats: ["image/avif", "image/webp"], minimumCacheTTL: 86400 }
};

export default nextConfig;
