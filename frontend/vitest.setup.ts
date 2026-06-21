import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// React Testing Library + vitest don't auto-cleanup the DOM between tests; an
// orphaned mount from the previous test will fail later queries unpredictably.
afterEach(() => cleanup());
