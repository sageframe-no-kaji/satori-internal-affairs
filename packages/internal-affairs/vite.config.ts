import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// Forward /api requests to the satori-api FastAPI server in dev.
			// This avoids CORS entirely during local development.
			// In production, a reverse proxy (nginx, etc.) would do the same.
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
			},
		},
	},
});
