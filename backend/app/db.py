from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import Session, SQLModel, create_engine

if TYPE_CHECKING:
    from .services import Treasurer

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "amanahpay.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    from . import models

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@lru_cache(maxsize=1)
def get_treasurer() -> "Treasurer":
    from .services import Treasurer

    return Treasurer()
