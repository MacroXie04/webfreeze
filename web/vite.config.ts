import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev the React app runs on :5173 and proxies API + resource-proxy calls to
// the local backend (default :8000, override with WF_BACKEND). This keeps every
// request same-origin from the browser's view, so the preview iframe's relative
// /proxy URLs resolve cleanly.
const BACKEND = process.env.WF_BACKEND ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": BACKEND,
      "/proxy": BACKEND,
    },
  },
  build: {
    // P5 will point this at src/webfreeze/server/static and have FastAPI serve it.
    outDir: "dist",
  },
});
