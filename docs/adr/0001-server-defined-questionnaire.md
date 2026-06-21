# ADR-0001 — Server-defined questionnaire

**Status:** Accepted
**Date:** 2026-04-08

## Context

The onboarding questionnaire is the **only** place a Day-0 footprint can come
from — there's no measured data on a new user. Two readers consume the same
list of questions:

1. The **client** renders inputs from it (`Questionnaire.tsx`).
2. The **estimator** does the math from it (`services/estimator.py`).

If those two ever disagree about which questions exist — a stray
``visibleIf``, a default value drift, an option key change — the estimate
silently goes wrong and we don't notice until a user complains. The easiest
way to keep them in lock-step is one source.

We considered three shapes:

* **Client-defined**: the React tree is the source; the backend exposes a
  generic key/value `/onboarding/answers` endpoint. Rejected because the
  estimator can't validate (it doesn't know which keys are real) and a
  client release becomes load-bearing for accuracy.
* **Schema-only contract** (e.g. JSON Schema): both sides validate against
  the same schema. Better, but doesn't capture **ordering**, ``visibleIf``
  conditions, or the R0 value-of-information scores — those are behavioral.
* **Server-defined data, client-rendered**: backend owns the canonical
  ``QUESTIONS`` list with help text, defaults, ranges, and conditional
  visibility. Client renders from `GET /onboarding/questions`. The
  estimator reads the same list.

## Decision

The questionnaire is **server-defined** in
[`services/questionnaire.py`](../../backend/app/services/questionnaire.py) as a
typed Python list (`QUESTIONS`) and exposed via
[`GET /api/v1/onboarding/questions`](../../backend/app/api/v1/onboarding.py).
The client never hard-codes questions.

The response is cached aggressively (`Cache-Control: public, max-age=3600,
immutable` + ETag keyed on ``QUESTIONNAIRE_VERSION``) — when the question
set is rev'd, the ETag changes and clients pick up the new payload on the
next request.

## Consequences

* The estimator and renderer **cannot** drift. A new question lands in
  both places with a single PR.
* Question copy / help text updates ship without a frontend release.
* R0 (value-of-information ordering, in
  [`services/voi.py`](../../backend/app/services/voi.py)) gets to mutate
  the list once at import time; the order the user sees is identical to
  the order the math considers.
* The shape (`Questionnaire` / `Question` Pydantic models, mirrored as TS
  `Questionnaire` / `Question` types) **is** the contract — typed both
  ends, breaking changes caught at typecheck.
* Cost: the client has to handle ``visibleIf`` (already does, mirrors the
  backend's ``is_visible``); the questionnaire is bigger over the wire
  than a static hash would be. Both are fine.
