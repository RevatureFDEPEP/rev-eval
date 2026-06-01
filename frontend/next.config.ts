import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Let Turbopack use system certificates when next/font fetches Google fonts during builds.
    turbopackUseSystemTlsCerts: true,
  },
};

export default nextConfig;
