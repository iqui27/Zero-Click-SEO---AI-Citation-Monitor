import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isDev = mode === 'development'

  // Define object to conditionally inject VITE_API_BASE
  const define: Record<string, string> = {}
  if (isDev && !env.VITE_API_BASE) {
    // Default to '/api' only in development when not provided
    define['import.meta.env.VITE_API_BASE'] = JSON.stringify('/api')
  } else if (env.VITE_API_BASE) {
    // In production (or dev), if provided, pass it through without hardcoding elsewhere
    define['import.meta.env.VITE_API_BASE'] = JSON.stringify(env.VITE_API_BASE)
  }

  return {
    plugins: [react()],
    define,
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
