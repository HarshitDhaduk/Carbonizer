"""Import all models so Alembic autogenerate and Base.metadata see them."""

from app.db.base import Base
from app.models.community import (
    Challenge,
    ChallengeParticipant,
    Cohort,
    UserCohort,
)
from app.models.connection import Connection
from app.models.emission import (
    CategoryRollup,
    EmissionFactor,
    FootprintSnapshot,
    LedgerEntry,
)
from app.models.ingestion import RawEnergyRead, RawTransaction, RawTrip
from app.models.onboarding import OnboardingProfile
from app.models.privacy import AuditLog, DsrJob, IdempotencyKey
from app.models.recommendation import Recommendation, RecommendationAction
from app.models.user import Consent, PrivacySettings, Session, User

__all__ = [
    "AuditLog",
    "Base",
    "CategoryRollup",
    "Challenge",
    "ChallengeParticipant",
    "Cohort",
    "Connection",
    "Consent",
    "DsrJob",
    "EmissionFactor",
    "FootprintSnapshot",
    "IdempotencyKey",
    "LedgerEntry",
    "OnboardingProfile",
    "PrivacySettings",
    "RawEnergyRead",
    "RawTransaction",
    "RawTrip",
    "Recommendation",
    "RecommendationAction",
    "Session",
    "User",
    "UserCohort",
]
