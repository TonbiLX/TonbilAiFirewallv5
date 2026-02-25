// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dev: Vite dev server (proxy -> Docker backend)
// Prod: npm run build -> statik dosyalar -> nginx tarafindan sunulur
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: ["guard.tonbilx.com", "192.168.1.9", "localhost"],
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
