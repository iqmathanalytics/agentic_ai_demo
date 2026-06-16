import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    // Raise chunk size warning threshold (cosmetic only)
    chunkSizeWarningLimit: 1000,
  },
});
