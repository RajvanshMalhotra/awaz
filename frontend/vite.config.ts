import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/pipeline': 'http://localhost:8000',
      '/onboarding': 'http://localhost:8000',
      '/tts_output': 'http://localhost:8000',
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
})
