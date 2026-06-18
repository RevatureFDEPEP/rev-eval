import "@testing-library/jest-dom"

// recharts' ResponsiveContainer relies on ResizeObserver, which jsdom doesn't
// implement. Provide a no-op stub so chart components can render in tests.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}
