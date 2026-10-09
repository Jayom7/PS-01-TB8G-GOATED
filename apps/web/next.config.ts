import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backend = process.env.API_INTERNAL_URL;
    return backend ? [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }] : [];
  },
  // OCR + bounded embedding can exceed the rewrite proxy's 30-second default.
  // Keep the 25 MB upload contract and the client's 180-second deadline aligned.
  experimental: { proxyTimeout: 180_000, proxyClientMaxBodySize: "26mb" },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
