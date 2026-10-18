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
    "postgresql+psycopg://amanah:amanah@localhost:5432/amanahpay",
)

if os.getenv("AMANAHPAY_DOCKER") != "1":
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
        )
        if table in inspector.get_table_names()
    }
    with engine.begin() as connection:
        for table, columns in columns_by_table.items():
            if "business_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN business_id VARCHAR"))
            if table == "sales_invoices" and "review_notes" not in columns:
                connection.execute(text("ALTER TABLE sales_invoices ADD COLUMN review_notes VARCHAR"))
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
