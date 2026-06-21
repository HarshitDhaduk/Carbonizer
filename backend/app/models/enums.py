"""Domain enums shared by ORM models and Pydantic schemas (docs/DB-SCHEMA.md §2).

These are the controlled vocabularies for the carbon-accounting model:
categories, calculation methods, source types, provider kinds, lifecycle
states, and Day-0 questionnaire choices. Every enum is `str`-backed so the
wire format and the DB representation are identical.
"""

from __future__ import annotations

import enum


class Category(str, enum.Enum):
    """The five emission domains the dashboard surfaces (docs/DESIGN.md §2)."""

    transport = "transport"
    energy = "energy"
    food = "food"
    spend = "spend"
    home = "home"


class CalcMethod(str, enum.Enum):
    """Data-quality tier — drives the Progressive Data Depth badge.

    Ordered worst → best: `estimated` (onboarding only) → `spend` (bank txns)
    → `activity` (metered kWh / km). The R1 ``imputed`` flag is orthogonal.
    """

    activity = "activity"
    spend = "spend"
    estimated = "estimated"


class SourceType(str, enum.Enum):
    """Discriminator on the polymorphic raw_* tables."""

    transaction = "transaction"
    trip = "trip"
    energy = "energy"


class ProviderKind(str, enum.Enum):
    """Which kind of third-party source feeds a Connection row."""

    bank = "bank"
    telematics = "telematics"
    meter = "meter"


class ConnStatus(str, enum.Enum):
    """Lifecycle of a user's Connection row (docs/UI-UX-DESIGN.md §6.4)."""

    disconnected = "disconnected"
    connecting = "connecting"
    connected = "connected"
    needs_attention = "needs_attention"


class TripMode(str, enum.Enum):
    """Detected travel mode from telematics ingestion."""

    car = "car"
    bus = "bus"
    train = "train"
    cycle = "cycle"
    walk = "walk"
    flight = "flight"
    other = "other"


class BiomeStatus(str, enum.Enum):
    """Living-Planet visual state — function of footprint health 0..1."""

    seed = "seed"
    regressing = "regressing"
    plateau = "plateau"
    improving = "improving"
    thriving = "thriving"


class Trend(str, enum.Enum):
    """Direction of a delta vs the prior period."""

    up = "up"
    down = "down"
    flat = "flat"


class NudgeKind(str, enum.Enum):
    """Behavioural nudge taxonomy (docs/UI-UX-DESIGN.md §7)."""

    action = "action"
    default_swap = "default-swap"
    clean_window = "clean-window"


class NudgeEffort(str, enum.Enum):
    """Effort tier surfaced on a nudge card — sets user expectations."""

    one_tap = "1-tap"
    five_min = "5-min"
    setup = "setup"


class NudgeStatus(str, enum.Enum):
    """User-driven state of a served nudge."""

    active = "active"
    acted = "acted"
    dismissed = "dismissed"
    expired = "expired"


class LocPrecision(str, enum.Enum):
    """User-selectable precision for stored location data (privacy control)."""

    precise = "precise"
    coarse_1km = "coarse_1km"
    event_only = "event_only"


class HomeType(str, enum.Enum):
    """Day-0 questionnaire answer — drives the home-energy prior."""

    flat = "flat"
    terraced = "terraced"
    semi = "semi"
    detached = "detached"


class EnergySource(str, enum.Enum):
    """Day-0 questionnaire answer — multiplies the home-energy factor."""

    standard = "standard"
    green = "green"
    renewable = "renewable"


class Diet(str, enum.Enum):
    """Day-0 questionnaire answer — drives the food category prior."""

    meat_heavy = "meat_heavy"
    average = "average"
    low_meat = "low_meat"
    vegetarian = "vegetarian"
    vegan = "vegan"


class CarType(str, enum.Enum):
    """Day-0 questionnaire answer — drives the transport prior; gates
    follow-up questions via visible_if."""

    none = "none"
    petrol = "petrol"
    diesel = "diesel"
    hybrid = "hybrid"
    ev = "ev"


class OnboardingStatus(str, enum.Enum):
    """Whether the user has finished the Day-0 questionnaire."""

    in_progress = "in_progress"
    completed = "completed"


class DsrKind(str, enum.Enum):
    """Which GDPR / DPDP data-rights flow a DsrJob represents."""

    export = "export"
    erase = "erase"


class JobStatus(str, enum.Enum):
    """Generic async-job state — used by dsr_jobs today."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
