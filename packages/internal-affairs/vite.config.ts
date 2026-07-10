import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit(), svelteTesting()],
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
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		setupFiles: ['./vitest-setup.ts'],
	},
});
