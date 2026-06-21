"""Value-of-information ordering for the onboarding questionnaire (R0).

Score each question by how much its answer can swing the total footprint
(holding the rest at defaults) — its information content. Order questions by
that score, highest-yield first, so the flow front-loads the questions that
most shrink the user's footprint uncertainty (docs/DATA-STRATEGY.md §9, R0;
composes with R1).

Exposes a single side-effecting entry point — :func:`apply_voi` — that mutates
the shared ``QUESTIONS`` list in place to:

  1. set ``q.voi`` to a normalised 0..1 score, and
  2. reorder the list so high-VoI questions come first, respecting each
     question's ``visible_if`` parent (a child never appears before its parent).

It's called at import time from :mod:`app.services.estimator` so every reader
sees the ordered, scored list without needing to know it exists.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.schemas.footprint import FootprintSummary
from app.schemas.onboarding import AnswerValue, Question

if TYPE_CHECKING:
    Estimator = Callable[[dict[str, AnswerValue]], FootprintSummary]


def _question_spread(
    q: Question, questions: list[Question], estimate: Estimator
) -> float:
    """Total-footprint spread (tCO2e) as ``q`` varies over its domain, others fixed."""
    base: dict[str, AnswerValue] = {qq.id: qq.default for qq in questions}
    totals: list[float] = []
    if q.type == "single":
        for opt in q.options or []:
            totals.append(estimate({**base, q.id: opt.value}).total_tco2e)
    else:
        lo, hi = q.min or 0, q.max if q.max is not None else 0
        for v in (lo, hi):
            totals.append(estimate({**base, q.id: v}).total_tco2e)
    return (max(totals) - min(totals)) if totals else 0.0


def _voi_order(questions: list[Question]) -> list[Question]:
    """Sort by VoI desc, but keep each question after its ``visible_if`` parent."""
    by_voi = sorted(questions, key=lambda q: q.voi or 0, reverse=True)
    by_id = {q.id: q for q in questions}
    placed: set[str] = set()
    result: list[Question] = []

    def place(q: Question) -> None:
        if q.id in placed:
            return
        parent_id = q.visible_if.question_id if q.visible_if else None
        if parent_id and parent_id in by_id:
            place(by_id[parent_id])
        placed.add(q.id)
        result.append(q)

    for q in by_voi:
        place(q)
    return result


def apply_voi(questions: list[Question], estimate: Estimator) -> None:
    """Score + reorder ``questions`` in place. Called once at module import."""
    spreads = {q.id: _question_spread(q, questions, estimate) for q in questions}
    mx = max(spreads.values()) or 1.0
    for q in questions:
        q.voi = round(spreads[q.id] / mx, 3)
    questions[:] = _voi_order(questions)
