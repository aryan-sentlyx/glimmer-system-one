import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

const BACKEND = process.env.VITE_BACKEND ?? 'https://aryan-59489--glimmer-demo.us-east.modal.run'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/examples': { target: BACKEND, changeOrigin: true },
    },
  },
})
