import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // API на том же origin: и локально, и в Telegram через один HTTPS-туннель.
    proxy: { '/api': process.env.API_URL ?? 'http://localhost:8001' },
    // Разрешаем открыть dev-сервер через туннель (cloudflared / ngrok).
    allowedHosts: true,
  },
});
