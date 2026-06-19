"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { FootprintSummary, OnboardingAnswers, Question } from "@/lib/types";
import { ApiError, clientApi } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import { AuthGate } from "./AuthGate";
import { Questionnaire } from "./Questionnaire";
import { EstimateReveal } from "./EstimateReveal";

/**
 * Orchestrates: auth gate → (returning user? → dashboard) → questionnaire → reveal.
 * A signed-in user who has already completed onboarding is routed straight to the
 * dashboard rather than being asked the questions again.
 */
export function OnboardingFlow() {
  const token = useAuthStore((s) => s.token);
  const loadMe = useAuthStore((s) => s.loadMe);
  const router = useRouter();

  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [summary, setSummary] = useState<FootprintSummary | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null = not yet checked, false = needs onboarding, true = already done (redirecting)
  const [completed, setCompleted] = useState<boolean | null>(null);
  // saved progress to resume a half-finished onboarding
  const [resume, setResume] = useState<{
    answers: OnboardingAnswers;
    step: number;
  } | null>(null);

  // wait for zustand-persist to rehydrate the token before deciding anything
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(useAuthStore.persist.hasHydrated());
    return useAuthStore.persist.onFinishHydration(() => setHydrated(true));
  }, []);

  // returning-user check: completed profile → straight to the dashboard
  useEffect(() => {
    if (!hydrated || !token || completed !== null || summary) return;
    let active = true;
    void loadMe();
    clientApi
      .getOnboardingProfile(token)
      .then((p) => {
        if (!active) return;
        if (p.completed) {
          setCompleted(true);
          router.replace("/dashboard");
        } else {
          if (p.answers) setResume({ answers: p.answers, step: p.currentStep });
          setCompleted(false);
        }
      })
      .catch((e) => {
        // on a 401 the token is stale; otherwise let them onboard
        if (!active) return;
        if (e instanceof ApiError && e.status === 401) {
          useAuthStore.getState().logout();
        } else {
          setCompleted(false);
        }
      });
    return () => {
      active = false;
    };
  }, [hydrated, token, completed, summary, loadMe, router]);

  // fetch the questionnaire once we know the user still needs onboarding
  useEffect(() => {
    if (!token || questions || completed !== false) return;
    let active = true;
    clientApi
      .getOnboardingQuestions(token)
      .then((q) => active && setQuestions(q.questions))
      .catch((e) => active && setError(messageFrom(e)));
    return () => {
      active = false;
    };
  }, [token, questions, completed]);

  // debounced autosave of partial progress (fires from the questionnaire)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleProgress = useCallback(
    (answers: OnboardingAnswers, step: number) => {
      if (!token) return;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        void clientApi
          .saveOnboardingProgress(token, answers, step)
          .catch(() => {
            /* autosave is best-effort; don't interrupt the user */
          });
      }, 500);
    },
    [token],
  );
  useEffect(() => () => void (saveTimer.current && clearTimeout(saveTimer.current)), []);

  async function handleComplete(answers: OnboardingAnswers) {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      setSummary(await clientApi.submitEstimate(token, answers));
    } catch (e) {
      setError(messageFrom(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg-base px-4 py-10">
      {!hydrated ? (
        <Loading label="Loading…" />
      ) : !token ? (
        <AuthGate />
      ) : completed !== false ? (
        // checking the profile, or redirecting a returning user straight to the
        // dashboard — stay silent (no message) until the route changes
        null
      ) : summary ? (
        <EstimateReveal summary={summary} />
      ) : questions ? (
        <div className="w-full max-w-md">
          {error && (
            <p role="alert" className="mb-3 text-center text-sm text-danger">
              {error}
            </p>
          )}
          <Questionnaire
            questions={questions}
            submitting={submitting}
            onComplete={handleComplete}
            onProgress={handleProgress}
            initialStep={resume?.step ?? 0}
            {...(resume ? { initialAnswers: resume.answers } : {})}
          />
        </div>
      ) : error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : (
        <Loading label="Setting up your questions…" />
      )}
    </main>
  );
}

function Loading({ label }: { label: string }) {
  return <div className="text-sm text-text-lo">{label}</div>;
}

function messageFrom(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
