import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The desk talks to the FastAPI backend at http://localhost:8000 (see src/api.ts).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, open: true },
})
