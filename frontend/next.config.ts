import type { NextConfig } from "next";

// The browser only ever talks to this Next.js origin; /api/* is proxied to the
// FastAPI backend. Same-origin means no CORS preflights and one public URL.
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
