"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";
import { PasswordField } from "./PasswordField";
import {
  isPasswordError,
  isPasswordMismatch,
  mismatchField,
} from "./auth-errors";

/**
 * Compact sign-in / create-account card. On success the backend sets HttpOnly
 * auth cookies, the store loads the user, and the parent flow re-renders into
 * the questionnaire.
 */
export function AuthGate() {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const status = useAuthStore((s) => s.status);
  const apiError = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const clearError = useAuthStore((s) => s.clearError);

  const loading = status === "loading";
  const isRegister = mode === "register";
  const error = formError ?? apiError;

  function clearErrors() {
    if (formError) setFormError(null);
    if (apiError) clearError();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (isRegister) {
      if (password !== confirm) {
        setFormError("Passwords don't match.");
        return;
      }
      await register(email.trim(), password);
    } else {
      await login(email.trim(), password);
    }
  }

  function toggleMode() {
    setMode(isRegister ? "login" : "register");
    setConfirm("");
    setFormError(null);
    clearError();
  }

  return (
    <div className="w-full max-w-sm animate-fade-rise">
      <div className="mb-6 flex flex-col items-center text-center">
        <Link
          href="/"
          aria-label="Carbonizer home"
          className="mb-4 rounded-md transition-opacity hover:opacity-80"
        >
          <Logo />
        </Link>
        <h1 className="font-display text-2xl text-text-hi">
          {isRegister ? "Create your account" : "Welcome back"}
        </h1>
        <p className="mt-1 text-sm text-text-mid">
          {isRegister
            ? "Two minutes to your first footprint."
            : "Sign in to continue."}
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="glass space-y-3 rounded-card p-5"
        aria-describedby={error ? "auth-error" : undefined}
        noValidate
      >
        {/* Error summary at the top of the form — screen readers hear the
            error before they walk back through the fields (WCAG 3.3.1). */}
        {error && (
          <div
            id="auth-error"
            role="alert"
            className="border-danger/40 bg-danger/10 rounded-md border px-3 py-2 text-sm text-danger"
          >
            <a href={`#${mismatchField(error)}`} className="underline">
              {error}
            </a>
          </div>
        )}

        <div>
          <label htmlFor="email" className="mb-1 block text-xs text-text-lo">
            Email <span className="text-danger">*</span>
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            aria-required="true"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              clearErrors();
            }}
            className="h-10 w-full rounded-md border border-border-strong bg-surface-1 px-3 text-text-hi placeholder:text-text-lo"
            placeholder="you@example.com"
          />
        </div>

        <PasswordField
          id="password"
          label="Password"
          value={password}
          onChange={(v) => {
            setPassword(v);
            clearErrors();
          }}
          autoComplete={isRegister ? "new-password" : "current-password"}
          placeholder={isRegister ? "At least 12 characters" : "Your password"}
          show={showPassword}
          onToggle={() => setShowPassword((s) => !s)}
          minLength={isRegister ? 12 : undefined}
          invalid={isPasswordError(error)}
          describedBy={isPasswordError(error) ? "auth-error" : undefined}
        />

        {isRegister && (
          <PasswordField
            id="confirm"
            label="Confirm password"
            value={confirm}
            onChange={(v) => {
              setConfirm(v);
              clearErrors();
            }}
            autoComplete="new-password"
            placeholder="Re-enter your password"
            show={showPassword}
            onToggle={() => setShowPassword((s) => !s)}
            minLength={12}
            invalid={isPasswordMismatch(error)}
            describedBy={isPasswordMismatch(error) ? "auth-error" : undefined}
          />
        )}

        <Button type="submit" size="lg" className="w-full" disabled={loading}>
          {loading
            ? "Just a moment…"
            : isRegister
              ? "Create account"
              : "Sign in"}
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-text-mid">
        {isRegister ? "Already have an account?" : "New to Carbonizer?"}{" "}
        <button
          type="button"
          onClick={toggleMode}
          className="font-medium text-brand-400 hover:text-brand-500"
        >
          {isRegister ? "Sign in" : "Create one"}
        </button>
      </p>
    </div>
  );
}
