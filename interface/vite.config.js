import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/console/',
  server: {
    // Fix for environments with low inotify/open-files limits (EMFILE).
    // Polling avoids creating too many filesystem watchers.
    watch: {
      usePolling: true,
      interval: 250,
    },
  },
})
