import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  reactCompiler: true,
  serverExternalPackages: ["three"],
  turbopack: {
    resolveAlias: {},
  },
};

export default nextConfig;
