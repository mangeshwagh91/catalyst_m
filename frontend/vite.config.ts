import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// Pure Vite + TanStack Router SPA build — works with Vercel static hosting.
// No SSR / Cloudflare workers needed for this app.
export default defineConfig({
  plugins: [
    TanStackRouterVite({
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routeTree.gen.ts",
    }),
    tailwindcss(),
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          router: ["@tanstack/react-router", "@tanstack/react-query"],
          charts: ["recharts"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to backend in dev
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
