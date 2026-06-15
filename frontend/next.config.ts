import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build de producción self-contained para ECS (node server.js).
  // Dev local sigue usando `next dev` vía docker-compose.
  output: "standalone",
};

export default nextConfig;
