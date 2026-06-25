import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/query':     { target: 'http://localhost:8000', changeOrigin: true },
      '/auth':      { target: 'http://localhost:8000', changeOrigin: true },
      '/customers': { target: 'http://localhost:8000', changeOrigin: true },
      '/issues':    { target: 'http://localhost:8000', changeOrigin: true },
      '/evals':     { target: 'http://localhost:8000', changeOrigin: true },
      '/health':    { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})
