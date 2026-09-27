import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// envDir stays this folder on purpose: the repo-root .env points at production.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5175, strictPort: true },
  preview: { port: 5175, strictPort: true },
  test: { environment: "jsdom", globals: true },
});
