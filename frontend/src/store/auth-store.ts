import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthUser } from "@/lib/types";
import { ApiError, clientApi } from "@/lib/client-api";

/**
 * Client-side auth: holds the current user (the JWT now lives in an HttpOnly
 * cookie set by the backend, so the SPA never touches it). The `user` field is
 * persisted to localStorage so a returning visitor sees their account state
 * before /auth/me has resolved — but the cookie is the source of truth.
 *
 * Phase 2.1 of docs/IMPROVEMENT-PLAN.md moved the JWT out of localStorage; XSS
 * can no longer exfiltrate it. CSRF is enforced server-side via a double-submit
 * `cb_csrf` cookie (see client-api.ts).
 */

type Status = "idle" | "loading";

export interface AuthState {
  user: AuthUser | null;
  status: Status;
  error: string | null;
  /** True once we've finished the first /auth/me probe — gates redirects. */
  hydrated: boolean;

  register: (
    email: string,
    password: string,
    region?: string,
  ) => Promise<boolean>;
  login: (email: string, password: string) => Promise<boolean>;
  loadMe: () => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

function messageFrom(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      status: "idle",
      error: null,
      hydrated: false,

      register: async (email, password, region = "GB") => {
        set({ status: "loading", error: null });
        try {
          await clientApi.registerUser(email, password, region);
          await get().loadMe();
          set({ status: "idle" });
          return true;
        } catch (err) {
          set({ status: "idle", error: messageFrom(err) });
          return false;
        }
      },

      login: async (email, password) => {
        set({ status: "loading", error: null });
        try {
          await clientApi.loginUser(email, password);
          await get().loadMe();
          set({ status: "idle" });
          return true;
        } catch (err) {
          set({ status: "idle", error: messageFrom(err) });
          return false;
        }
      },

      loadMe: async () => {
        try {
          const user = await clientApi.getMe();
          set({ user, hydrated: true });
        } catch (err) {
          // 401 → no valid cookie → clear cached user; everything else → keep
          // the cached user but still mark hydrated so the UI can move on.
          if (err instanceof ApiError && err.status === 401) {
            set({ user: null, hydrated: true });
          } else {
            set({ hydrated: true });
          }
        }
      },

      logout: async () => {
        try {
          await clientApi.logout();
        } catch {
          /* logout is idempotent — failure to clear server-side is non-fatal */
        }
        set({ user: null, error: null });
      },
      clearError: () => set({ error: null }),
    }),
    {
      name: "carbonizer-auth",
      // Persist `user` for instant first paint; never persist transient state.
      // `hydrated` is recomputed each session from the /me probe.
      partialize: (s) => ({ user: s.user }),
    },
  ),
);
