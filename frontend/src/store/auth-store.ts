import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthUser } from "@/lib/types";
import { ApiError, clientApi } from "@/lib/client-api";

/**
 * Client-side auth: holds the JWT access token (persisted to localStorage) and the
 * current user. Backs the onboarding flow, which requires an authenticated user.
 * Note: localStorage tokens are fine for this stage; a production app should prefer
 * httpOnly refresh cookies (the backend already issues them).
 */

type Status = "idle" | "loading";

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
  status: Status;
  error: string | null;

  register: (email: string, password: string, region?: string) => Promise<boolean>;
  login: (email: string, password: string) => Promise<boolean>;
  loadMe: () => Promise<void>;
  logout: () => void;
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
      token: null,
      user: null,
      status: "idle",
      error: null,

      register: async (email, password, region = "GB") => {
        set({ status: "loading", error: null });
        try {
          const { accessToken } = await clientApi.registerUser(email, password, region);
          set({ token: accessToken });
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
          const { accessToken } = await clientApi.loginUser(email, password);
          set({ token: accessToken });
          await get().loadMe();
          set({ status: "idle" });
          return true;
        } catch (err) {
          set({ status: "idle", error: messageFrom(err) });
          return false;
        }
      },

      loadMe: async () => {
        const { token } = get();
        if (!token) return;
        try {
          const user = await clientApi.getMe(token);
          set({ user });
        } catch (err) {
          // token expired / invalid → drop it
          if (err instanceof ApiError && err.status === 401) {
            set({ token: null, user: null });
          }
        }
      },

      logout: () => set({ token: null, user: null, error: null }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "carbonizer-auth",
      // only persist the token + user, not transient status/error
      partialize: (s) => ({ token: s.token, user: s.user }),
    },
  ),
);
