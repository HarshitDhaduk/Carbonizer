import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, clientApi } from "./client-api";

/**
 * Session rotation on 401 (audit/2026-08, M6).
 *
 * The access cookie lives 15 minutes and the refresh cookie 30 days, but
 * nothing ever called /auth/refresh — so the first request after the access
 * cookie aged out 401'd, `loadMe` cleared the user, and `useAuthGuard` bounced
 * a still-authenticated visitor to onboarding.
 */

type FetchArgs = [input: RequestInfo | URL, init?: RequestInit];

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function pathOf(args: FetchArgs): string {
  return String(args[0]);
}

function methodOf(args: FetchArgs): string {
  return args[1]?.method ?? "GET";
}

describe("client-api — refresh on 401", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rotates the session and replays the original request", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Not authenticated" }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse(200, { email: "demo@carbonizer.app" }),
      );

    const user = await clientApi.getMe();

    expect(user).toEqual({ email: "demo@carbonizer.app" });
    const calls = fetchMock.mock.calls as FetchArgs[];
    expect(calls).toHaveLength(3);
    expect(pathOf(calls[0]!)).toContain("/auth/me");
    expect(pathOf(calls[1]!)).toContain("/auth/refresh");
    expect(methodOf(calls[1]!)).toBe("POST");
    expect(pathOf(calls[2]!)).toContain("/auth/me");
  });

  it("surfaces the original 401 when the refresh also fails", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Not authenticated" }))
      .mockResolvedValueOnce(
        jsonResponse(401, { detail: "Not authenticated" }),
      );

    await expect(clientApi.getMe()).rejects.toBeInstanceOf(ApiError);
    // Original + one refresh attempt, then it gives up — no retry storm.
    expect(fetchMock.mock.calls).toHaveLength(2);
  });

  it("does not retry a failed login — that 401 is a wrong password", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, { detail: "Incorrect email or password" }),
    );

    await expect(
      clientApi.loginUser("demo@carbonizer.app", "wrong"),
    ).rejects.toThrow("Incorrect email or password");
    expect(fetchMock.mock.calls).toHaveLength(1);
  });

  it("does not retry the refresh endpoint itself", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, { detail: "Not authenticated" }),
    );

    await expect(clientApi.refresh()).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock.mock.calls).toHaveLength(1);
  });

  it("passes non-401 errors straight through", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(500, { detail: "boom" }));

    await expect(clientApi.getMe()).rejects.toThrow("boom");
    expect(fetchMock.mock.calls).toHaveLength(1);
  });

  it("shares one rotation across concurrent 401s", async () => {
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/auth/refresh")) {
          return Promise.resolve(new Response(null, { status: 204 }));
        }
        // Every first-attempt read 401s; the replay after refresh succeeds.
        const attempted = fetchMock.mock.calls.filter(
          (c) =>
            String(c[0]) === path &&
            (c[1]?.method ?? "GET") === (init?.method ?? "GET"),
        ).length;
        return Promise.resolve(
          attempted > 1
            ? jsonResponse(200, [])
            : jsonResponse(401, { detail: "Not authenticated" }),
        );
      },
    );

    await Promise.all([
      clientApi.getRecommendations(),
      clientApi.getConnections(),
    ]);

    const refreshCalls = (fetchMock.mock.calls as FetchArgs[]).filter((c) =>
      pathOf(c).includes("/auth/refresh"),
    );
    expect(refreshCalls).toHaveLength(1);
  });
});
