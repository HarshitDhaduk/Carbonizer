"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/cn";

/**
 * Compact sign-in / create-account card. On success the auth store sets the token,
 * which re-renders the parent flow into the questionnaire.
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
    <div className="animate-fade-rise w-full max-w-sm">
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

      <form onSubmit={onSubmit} className="glass space-y-3 rounded-card p-5">
        <div>
          <label htmlFor="email" className="mb-1 block text-xs text-text-lo">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
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
          placeholder={isRegister ? "At least 8 characters" : "Your password"}
          show={showPassword}
          onToggle={() => setShowPassword((s) => !s)}
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
          />
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
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

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  show,
  onToggle,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  placeholder: string;
  show: boolean;
  onToggle: () => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs text-text-lo">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? "text" : "password"}
          autoComplete={autoComplete}
          required
          minLength={8}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "h-10 w-full rounded-md border border-border-strong bg-surface-1 pl-3 pr-10 text-text-hi placeholder:text-text-lo",
          )}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={onToggle}
          aria-label={show ? "Hide password" : "Show password"}
          aria-pressed={show}
          className="absolute right-2 top-1/2 -translate-y-1/2 grid h-7 w-7 place-items-center rounded text-text-lo transition-colors hover:text-text-hi"
        >
          {show ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
        </button>
      </div>
    </div>
  );
}
