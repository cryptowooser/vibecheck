import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 5178,
    proxy: {
      '/api': {
        target: 'http://localhost:8780',
        changeOrigin: true,
      },
    },
  },
})
