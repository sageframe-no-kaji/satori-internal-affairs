import '@testing-library/jest-dom/vitest';

// jsdom has no layout engine and does not implement scrollIntoView; the
// concerns panel calls it when fresh evidence arrives.
if (!Element.prototype.scrollIntoView) {
	Element.prototype.scrollIntoView = () => {};
}
