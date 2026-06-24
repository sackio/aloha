import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Aloha",
        short_name: "Aloha",
        theme_color: "#0ea5e9",
        background_color: "#0f172a",
        display: "standalone",
        icons: [
          {
            src: "/manifest.json",
            sizes: "any",
            type: "image/svg+xml",
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": "http://localhost:7123",
      "/auth": "http://localhost:7123",
      "/health": "http://localhost:7123",
      "/mcp": "http://localhost:7123",
    },
  },
  build: {
    outDir: "../aloha/static",
    emptyOutDir: true,
  },
});
