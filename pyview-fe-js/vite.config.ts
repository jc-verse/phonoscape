import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react({ include: /\.(?:mmd|js|jsx|ts|tsx)$/u })],
  define: { "process.env": { NODE_ENV: JSON.stringify(process.env.NODE_ENV) } },
  build: { cssCodeSplit: false, target: "es2022" },
  resolve: {
    mainFields: ["main"],
    alias: {
      assets: fileURLToPath(new URL("./assets", import.meta.url)),
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
