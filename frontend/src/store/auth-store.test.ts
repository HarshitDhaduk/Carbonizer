import { describe, expect, it, vi, beforeEach } from "vitest";
import type { AuthUser } from "@/lib/types";

const USER: AuthUser = {
  id: "u1",
  email: "alice@example.com",
  region: "GB",
  targetTco2e: 3.5,
};

// Mock the API module before importing the store (the store grabs clientApi at
// module init through the closure of its actions).
const apiMocks = vi.hoisted(() => ({
  loginUser: vi.fn(async () => ({
    accessToken: "ignored-now-cookies",
    tokenType: "bearer",
    expiresIn: 900,
  })),
  registerUser: vi.fn(async () => ({
    accessToken: "ignored-now-cookies",
    tokenType: "bearer",
    expiresIn: 900,
  })),
  getMe: vi.fn(async () => USER),
  logout: vi.fn(async () => undefined),
}));

vi.mock("@/lib/client-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/client-api")>(
    "@/lib/client-api",
  );
  return {
    ...actual,
    clientApi: apiMocks,
  };
});

beforeEach(async () => {
  Object.values(apiMocks).forEach((m) => m.mockClear());
  apiMocks.getMe.mockImplementation(async () => USER);
  const { useAuthStore } = await import("./auth-store");
  useAuthStore.setState({
    user: null,
    status: "idle",
    error: null,
    hydrated: false,
  });
});

describe("useAuthStore", () => {
  it("login → loadMe populates user and clears loading", async () => {
    const { useAuthStore } = await import("./auth-store");
    const ok = await useAuthStore.getState().login("a@b.com", "12-chars-strong");
    expect(ok).toBe(true);
    expect(apiMocks.loginUser).toHaveBeenCalledWith("a@b.com", "12-chars-strong");
    expect(useAuthStore.getState().user).toEqual(USER);
    expect(useAuthStore.getState().status).toBe("idle");
    expect(useAuthStore.getState().error).toBeNull();
  });

  it("login surfaces the API error message and returns false on failure", async () => {
    const { ApiError } = await import("@/lib/client-api");
    apiMocks.loginUser.mockRejectedValueOnce(
      new ApiError(401, "Incorrect email or password"),
    );
    const { useAuthStore } = await import("./auth-store");
    const ok = await useAuthStore.getState().login("a@b.com", "wrong");
    expect(ok).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().error).toBe("Incorrect email or password");
  });

  it("loadMe marks hydrated even when /me 401s (and clears any cached user)", async () => {
    const { ApiError } = await import("@/lib/client-api");
    apiMocks.getMe.mockRejectedValueOnce(new ApiError(401, "Not authenticated"));
    const { useAuthStore } = await import("./auth-store");
    useAuthStore.setState({ user: USER });
    await useAuthStore.getState().loadMe();
    expect(useAuthStore.getState().hydrated).toBe(true);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("logout calls the API to wipe cookies and clears user state", async () => {
    const { useAuthStore } = await import("./auth-store");
    useAuthStore.setState({ user: USER });
    await useAuthStore.getState().logout();
    expect(apiMocks.logout).toHaveBeenCalledOnce();
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("logout swallows API failures (idempotent — server-side may already be gone)", async () => {
    apiMocks.logout.mockRejectedValueOnce(new Error("network down"));
    const { useAuthStore } = await import("./auth-store");
    useAuthStore.setState({ user: USER });
    await useAuthStore.getState().logout();
    // No crash; local state still cleared.
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("clearError wipes the error field", async () => {
    const { useAuthStore } = await import("./auth-store");
    useAuthStore.setState({ error: "stale message" });
    useAuthStore.getState().clearError();
    expect(useAuthStore.getState().error).toBeNull();
  });
});
