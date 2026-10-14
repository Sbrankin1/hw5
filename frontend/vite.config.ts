import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The board talks straight to the FastAPI backend on :8000 (CORS allows this origin).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
