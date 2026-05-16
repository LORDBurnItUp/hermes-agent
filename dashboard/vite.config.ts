/// <reference types="node" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// VITE_SSE_URL can override the SSE endpoint at build time. The default
// path (/swarm/events) assumes the dashboard is served from the same
// FastAPI app that attached swarm.sse.attach_live_view(...).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5174,
      proxy: {
        "/swarm": {
          target: env.VITE_API_PROXY || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
