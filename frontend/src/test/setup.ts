import "@testing-library/jest-dom/vitest";

// Recharts' ResponsiveContainer needs a non-zero size in jsdom.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver =
  globalThis.ResizeObserver || ResizeObserverStub;
