import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Re-enable minification for production performance
    minify: 'esbuild', // or 'terser' for more aggressive minification
    // Keep sourcemaps for debugging in production if needed
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: undefined,
      }
    }
  }
})
