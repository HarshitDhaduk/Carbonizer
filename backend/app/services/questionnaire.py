"""Onboarding questionnaire — the server-defined source of truth.

The client renders these questions verbatim; the estimator consumes the same
``QUESTIONS`` list to compute the footprint. Sharing the definition prevents
the renderer and the math from disagreeing about which inputs exist.

This module exposes the questionnaire data and the visibility / normalization
helpers. The actual carbon math lives in :mod:`app.services.estimator`; the
value-of-information ordering lives in :mod:`app.services.voi`.
"""

from __future__ import annotations

from app.schemas.onboarding import (
    AnswerValue,
    Question,
    Questionnaire,
    QuestionOption,
    VisibleIf,
)

QUESTIONNAIRE_VERSION = 2

# Ordered by value-of-information: the largest footprint drivers first (transport,
# diet) so we get strong early signal and can keep the flow short. `visibleIf` skips
# irrelevant questions (e.g. car km when the user has no car).

QUESTIONS: list[Question] = [
    Question(
        id="carType", type="single", label="Your main car", default="petrol",
        help="Pick the one you use most. No car? We'll skip the rest of this.",
        options=[
            QuestionOption(value="none", label="No car"),
            QuestionOption(value="petrol", label="Petrol"),
            QuestionOption(value="diesel", label="Diesel"),
            QuestionOption(value="hybrid", label="Hybrid"),
            QuestionOption(value="ev", label="Electric"),
        ],
    ),
    Question(
        id="carKmPerWeek", type="number", label="How far do you drive a week?",
        min=0, max=2000, step=10, default=100, unit="km",
        help="A rough typical week is fine.",
        visible_if=VisibleIf(question_id="carType", not_equals="none"),
    ),
    Question(
        id="shortFlightsPerYear", type="number",
        label="Short flights a year", min=0, max=50, step=1, default=1,
        help="Return trips under ~4 hours (e.g. within Europe).",
    ),
    Question(
        id="longFlightsPerYear", type="number",
        label="Long-haul flights a year", min=0, max=30, step=1, default=0,
        help="Return trips over ~4 hours (e.g. intercontinental).",
    ),
    Question(
        id="diet", type="single", label="Your diet", default="average",
        options=[
            QuestionOption(value="meat_heavy", label="Meat with most meals"),
            QuestionOption(value="average", label="Average"),
            QuestionOption(value="low_meat", label="Low meat"),
            QuestionOption(value="vegetarian", label="Vegetarian"),
            QuestionOption(value="vegan", label="Vegan"),
        ],
    ),
    Question(
        id="homeType", type="single", label="Your home", default="terraced",
        options=[
            QuestionOption(value="flat", label="Flat"),
            QuestionOption(value="terraced", label="Terraced"),
            QuestionOption(value="semi", label="Semi-detached"),
            QuestionOption(value="detached", label="Detached"),
        ],
    ),
    Question(
        id="energySource", type="single", label="Home energy", default="standard",
        help="A green tariff or your own solar lowers your electricity emissions.",
        options=[
            QuestionOption(value="standard", label="Standard tariff"),
            QuestionOption(value="green", label="Green tariff"),
            QuestionOption(value="renewable", label="Mostly my own renewable"),
        ],
    ),
    Question(
        id="householdSize", type="number", label="People in your household",
        min=1, max=12, step=1, default=2,
        help="Home energy is shared across everyone who lives with you.",
    ),
]


def is_visible(q: Question, answers: dict[str, AnswerValue]) -> bool:
    """Whether a question is relevant given the answers so far (mirrors the
    frontend `isVisible`)."""
    cond = q.visible_if
    if cond is None:
        return True
    other = answers.get(cond.question_id)
    if cond.equals is not None:
        return other == cond.equals
    if cond.not_equals is not None:
        return other != cond.not_equals
    if cond.any_of is not None:
        return other in cond.any_of
    return True


def build_questionnaire() -> Questionnaire:
    """Return the server-defined Day-0 questionnaire payload (current version)."""
    return Questionnaire(version=QUESTIONNAIRE_VERSION, questions=QUESTIONS)


def normalize_answers(raw: dict[str, AnswerValue]) -> dict[str, AnswerValue]:
    """Fill defaults, validate option keys, clamp numbers. Forgiving by design."""
    out: dict[str, AnswerValue] = {}
    for q in QUESTIONS:
        val = raw.get(q.id, q.default)
        if q.type == "number":
            try:
                num = int(val)
            except (TypeError, ValueError):
                num = int(q.default)
            if q.min is not None:
                num = max(q.min, num)
            if q.max is not None:
                num = min(q.max, num)
            out[q.id] = num
        else:  # single-choice
            valid = {o.value for o in (q.options or [])}
            out[q.id] = val if val in valid else q.default

    # neutralize hidden questions (e.g. car km when carType == none) so an
    # irrelevant leftover answer can't contribute to the estimate
    for q in QUESTIONS:
        if not is_visible(q, out):
            out[q.id] = 0 if q.type == "number" else q.default
    return out
