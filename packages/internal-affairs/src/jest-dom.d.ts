// Pulls @testing-library/jest-dom's vitest Assertion augmentation into the
// project's type program — the runtime import lives in vitest-setup.ts,
// which sits outside src/ and is invisible to svelte-check.
import '@testing-library/jest-dom/vitest';
