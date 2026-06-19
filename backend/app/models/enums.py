"""Domain enums shared by ORM models and Pydantic schemas (docs/DB-SCHEMA.md §2)."""

from __future__ import annotations

import enum


class Category(str, enum.Enum):
    transport = "transport"
    energy = "energy"
    food = "food"
    spend = "spend"
    home = "home"


class CalcMethod(str, enum.Enum):
    activity = "activity"
    spend = "spend"
    estimated = "estimated"


class SourceType(str, enum.Enum):
    transaction = "transaction"
    trip = "trip"
    energy = "energy"


class ProviderKind(str, enum.Enum):
    bank = "bank"
    telematics = "telematics"
    meter = "meter"


class ConnStatus(str, enum.Enum):
    disconnected = "disconnected"
    connecting = "connecting"
    connected = "connected"
    needs_attention = "needs_attention"


class TripMode(str, enum.Enum):
    car = "car"
    bus = "bus"
    train = "train"
    cycle = "cycle"
    walk = "walk"
    flight = "flight"
    other = "other"


class BiomeStatus(str, enum.Enum):
    seed = "seed"
    regressing = "regressing"
    plateau = "plateau"
    improving = "improving"
    thriving = "thriving"


class Trend(str, enum.Enum):
    up = "up"
    down = "down"
    flat = "flat"


class NudgeKind(str, enum.Enum):
    action = "action"
    default_swap = "default-swap"
    clean_window = "clean-window"


class NudgeEffort(str, enum.Enum):
    one_tap = "1-tap"
    five_min = "5-min"
    setup = "setup"


class NudgeStatus(str, enum.Enum):
    active = "active"
    acted = "acted"
    dismissed = "dismissed"
    expired = "expired"


class LocPrecision(str, enum.Enum):
    precise = "precise"
    coarse_1km = "coarse_1km"
    event_only = "event_only"


class HomeType(str, enum.Enum):
    flat = "flat"
    terraced = "terraced"
    semi = "semi"
    detached = "detached"


class EnergySource(str, enum.Enum):
    standard = "standard"
    green = "green"
    renewable = "renewable"


class Diet(str, enum.Enum):
    meat_heavy = "meat_heavy"
    average = "average"
    low_meat = "low_meat"
    vegetarian = "vegetarian"
    vegan = "vegan"


class CarType(str, enum.Enum):
    none = "none"
    petrol = "petrol"
    diesel = "diesel"
    hybrid = "hybrid"
    ev = "ev"


class OnboardingStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"


class DsrKind(str, enum.Enum):
    export = "export"
    erase = "erase"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
