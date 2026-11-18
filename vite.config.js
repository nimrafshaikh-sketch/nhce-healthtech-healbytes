import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-icons": ["lucide-react"],
          "vendor-qr": ["jsqr", "qrcode.react"],
        },
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    watch: {
      ignored: ['**/get shit/**']
    }
  },
});
