"""default partitions for partitioned tables

The raw_* / ledger_entries / audit_log tables are declared PARTITION BY RANGE but
the initial migration created only the parents — so they reject inserts ("no
partition found for row"). For local/dev we attach a DEFAULT partition to each so
they accept any row. Production should instead manage monthly partitions with
pg_partman (DB-SCHEMA §10) and detach/drop the default.

Revision ID: c3f1a2b4d5e6
Revises: a25fb626e0c4
"""

from __future__ import annotations

from alembic import op

revision = "c3f1a2b4d5e6"
down_revision = "a25fb626e0c4"
branch_labels = None
depends_on = None

_PARTITIONED = [
    "raw_transactions",
    "raw_trips",
    "raw_energy_reads",
    "ledger_entries",
    "audit_log",
]


def upgrade() -> None:
    for table in _PARTITIONED:
        op.execute(
            f"CREATE TABLE IF NOT EXISTS {table}_default "
            f"PARTITION OF {table} DEFAULT"
        )


def downgrade() -> None:
    for table in _PARTITIONED:
        op.execute(f"DROP TABLE IF EXISTS {table}_default")
