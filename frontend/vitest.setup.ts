// Vitest global setup. Imported once before any test file (wired via
// vitest.config.ts -> test.setupFiles). Extends `expect` with the
// @testing-library/jest-dom matchers (toBeInTheDocument, toHaveTextContent, …)
// and unmounts rendered components after each test so DOM state never leaks
// between tests (this project does not enable vitest `globals`, so the
// library's automatic afterEach cleanup is not otherwise registered).
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
