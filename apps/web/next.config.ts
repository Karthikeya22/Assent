import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";
import path from "node:path";

// One .env at the repo root serves the API, worker and web. forceReload: Next has already
// loaded (and cached) apps/web's env by now, so without it this call silently does nothing.
loadEnvConfig(path.resolve(__dirname, "../.."), process.env.NODE_ENV !== "production", console, true);

// No dev badge: scripted screenshots (posters, product screens) are taken from the dev server.
const nextConfig: NextConfig = { devIndicators: false };

export default nextConfig;
