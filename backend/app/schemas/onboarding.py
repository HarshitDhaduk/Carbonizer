"""Onboarding questionnaire + estimate schemas (docs/API-DESIGN.md §10)."""

from __future__ import annotations

from typing import Literal

from app.schemas.common import CamelModel

# answer values are either a chosen option key (str) or a number (int)
AnswerValue = int | str


class QuestionOption(CamelModel):
    value: str
    label: str


class VisibleIf(CamelModel):
    """Show the question only when another answer satisfies this condition.

    Exactly one of equals / not_equals / any_of is set. Serializes camelCase
    (`questionId`, `notEquals`, `anyOf`) so the React renderer and the Python
    estimator evaluate identical rules.
    """

    question_id: str
    equals: AnswerValue | None = None
    not_equals: AnswerValue | None = None
    any_of: list[AnswerValue] | None = None


class Question(CamelModel):
    id: str
    type: Literal["single", "number"]
    label: str
    options: list[QuestionOption] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    unit: str | None = None
    help: str | None = None
    visible_if: VisibleIf | None = None
    # R0: value-of-information 0..1 — how much answering this shrinks footprint
    # uncertainty (the questions are ordered by it, highest-yield first).
    voi: float | None = None
    default: AnswerValue


class Questionnaire(CamelModel):
    version: int
    questions: list[Question]


class OnboardingAnswers(CamelModel):
    """Submitted answers, keyed by question id. Missing keys fall back to defaults."""

    answers: dict[str, AnswerValue]


class OnboardingProgress(CamelModel):
    """Autosaved partial progress — answers so far + the step the user is on."""

    answers: dict[str, AnswerValue]
    current_step: int = 0


class OnboardingProfileOut(CamelModel):
    status: Literal["in_progress", "completed"]
    completed: bool
    current_step: int
    answers: dict[str, AnswerValue] | None = None
