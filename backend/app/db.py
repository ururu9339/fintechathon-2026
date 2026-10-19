from functools import lru_cache
import os
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

if TYPE_CHECKING:
    from .services import Treasurer


_configured_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://qyzeai:qyzeai@localhost:5432/qyzeai",
)

if os.getenv("QYZEAI_DOCKER") != "1":
    _database_parts = urlsplit(_configured_database_url)
    if _database_parts.hostname == "db":
        _configured_database_url = urlunsplit(
            (
                _database_parts.scheme,
                _database_parts.netloc.replace("@db", "@localhost"),
                _database_parts.path,
                _database_parts.query,
                _database_parts.fragment,
            )
        )

DATABASE_URL = _configured_database_url
engine = create_engine(DATABASE_URL, echo=True)


def init_db() -> None:
    from . import models

    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    columns_by_table = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in (
            "ap_invoices",
            "sales_invoices",
            "employees",
            "payroll_runs",
            "payroll_records",
            "credit_facilities",
            "journal_entries",
            "ledger_accounts",
            "mandates",
            "counterparties",
            "payment_requests",
            "credit_dossiers",
            "users",
            "forecast_snapshots",
            "assistant_messages",
            "audit_events",
        )
        if table in inspector.get_table_names()
    }
    with engine.begin() as connection:
        for table, columns in columns_by_table.items():
            if "business_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN business_id VARCHAR"))
            if (
                table == "ap_invoices"
                and "mandate_id" in columns
                and engine.dialect.name == "postgresql"
            ):
                connection.execute(text("ALTER TABLE ap_invoices ALTER COLUMN mandate_id DROP NOT NULL"))
            if table == "mandates" and "status" not in columns:
                connection.execute(text("ALTER TABLE mandates ADD COLUMN status VARCHAR DEFAULT 'active'"))
            if table == "mandates":
                if "allowed_counterparty_ids" not in columns:
                    connection.execute(text("ALTER TABLE mandates ADD COLUMN allowed_counterparty_ids JSON"))
                if "auto_pay" not in columns:
                    connection.execute(text("ALTER TABLE mandates ADD COLUMN auto_pay BOOLEAN DEFAULT FALSE"))
                if "require_verified_supplier" not in columns:
                    connection.execute(text("ALTER TABLE mandates ADD COLUMN require_verified_supplier BOOLEAN DEFAULT TRUE"))
            if table == "counterparties":
                if "is_verified" not in columns:
                    connection.execute(text("ALTER TABLE counterparties ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
                if "provider_reference" not in columns:
                    connection.execute(text("ALTER TABLE counterparties ADD COLUMN provider_reference VARCHAR"))
            if table == "ap_invoices":
                if "source_system" not in columns:
                    connection.execute(text("ALTER TABLE ap_invoices ADD COLUMN source_system VARCHAR"))
                if "source_event_id" not in columns:
                    connection.execute(text("ALTER TABLE ap_invoices ADD COLUMN source_event_id VARCHAR"))
                if "source_invoice_id" not in columns:
                    connection.execute(text("ALTER TABLE ap_invoices ADD COLUMN source_invoice_id VARCHAR"))
            if table == "payment_requests":
                if "counterparty_id" not in columns:
                    connection.execute(text("ALTER TABLE payment_requests ADD COLUMN counterparty_id VARCHAR"))
                if "supplier_verified" not in columns:
                    connection.execute(text("ALTER TABLE payment_requests ADD COLUMN supplier_verified BOOLEAN DEFAULT FALSE"))
            if table == "sales_invoices" and "review_notes" not in columns:
                connection.execute(text("ALTER TABLE sales_invoices ADD COLUMN review_notes VARCHAR"))
            if table == "credit_dossiers":
                if "narrative_status" not in columns:
                    connection.execute(text("ALTER TABLE credit_dossiers ADD COLUMN narrative_status VARCHAR DEFAULT 'not_generated'"))
                if "narrative_text" not in columns:
                    connection.execute(text("ALTER TABLE credit_dossiers ADD COLUMN narrative_text TEXT"))
                if "narrative_model" not in columns:
                    connection.execute(text("ALTER TABLE credit_dossiers ADD COLUMN narrative_model VARCHAR"))
                if "narrative_prompt_version" not in columns:
                    connection.execute(text("ALTER TABLE credit_dossiers ADD COLUMN narrative_prompt_version VARCHAR"))
                if "pdf_generated_at" not in columns:
                    connection.execute(text("ALTER TABLE credit_dossiers ADD COLUMN pdf_generated_at TIMESTAMP WITH TIME ZONE"))
            if table == "users":
                if "email_verified_at" not in columns:
                    connection.execute(text("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP WITH TIME ZONE"))
                if "deleted_at" not in columns:
                    connection.execute(text("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE"))
                if "password_changed_at" not in columns:
                    connection.execute(text("ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP WITH TIME ZONE"))
            if table in {"ap_invoices", "sales_invoices"}:
                if "counterparty_id" not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN counterparty_id VARCHAR"))
                if table == "sales_invoices" and "myinvois_uuid" not in columns:
                    connection.execute(text("ALTER TABLE sales_invoices ADD COLUMN myinvois_uuid VARCHAR"))
                if "myinvois_validation_status" not in columns:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN myinvois_validation_status VARCHAR DEFAULT 'missing'")
                    )


def get_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


@lru_cache(maxsize=1)
def get_treasurer() -> "Treasurer":
    from .services import Treasurer

    return Treasurer()
