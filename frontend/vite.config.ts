import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, ".", "");
  const proxyTarget = environment.VITE_BACKEND_PROXY_TARGET?.trim();
  return {
    plugins: [react()],
    server: {
      host: environment.VITE_DEV_HOST || "0.0.0.0",
      port: Number(environment.VITE_DEV_PORT || "5173"),
      proxy: proxyTarget
        ? {
            "/api": {
              target: proxyTarget,
              changeOrigin: true,
            },
          }
        : undefined,
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      css: true,
    },
  };
});
