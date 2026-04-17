import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-only proxy target. Override with VITE_DEV_PROXY_TARGET when the backend
// runs somewhere other than http://localhost:8000 (e.g. remote tunnel, Docker).
const DEV_PROXY_TARGET = process.env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_APP_BASE || "/",
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/ui": DEV_PROXY_TARGET,
      "/agent": DEV_PROXY_TARGET,
      "/admin": DEV_PROXY_TARGET,
      "/health": DEV_PROXY_TARGET,
      "/v1": DEV_PROXY_TARGET,
      "/api": DEV_PROXY_TARGET,
    },
  },
});

