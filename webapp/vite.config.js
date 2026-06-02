import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
    },
    proxy: {
      '/api': 'http://localhost:8080'
    },
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'jackqueline-inversive-materially.ngrok-free.dev'
    ]
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
})