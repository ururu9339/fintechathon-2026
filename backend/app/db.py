from functools import lru_cache
import os
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import Session, SQLModel, create_engine

if TYPE_CHECKING:
    from .services import Treasurer

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://amanah:amanah@localhost:5432/amanahpay" #connect to postgresql database if DATABASE_URL is set, otherwise connect to sqlite database
)
# too connect to amanah.db DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "amanahpay.db"
#DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
# engine = create_engine(
#     f"sqlite:///{DATABASE_PATH}",
#     connect_args={"check_same_thread": False},
# )
engine = create_engine(DATABASE_URL, echo=True)    


def init_db() -> None:
    from . import models

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


@lru_cache(maxsize=1)
def get_treasurer() -> "Treasurer":
    from .services import Treasurer

    return Treasurer()
