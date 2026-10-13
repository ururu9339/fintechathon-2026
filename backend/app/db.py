"""Storage boundary for the MVP.

The demo uses process-local storage so it runs without setup; this module is the
single seam to replace with PostgreSQL repositories in the next milestone.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .services import Treasurer


@lru_cache(maxsize=1)
def get_treasurer() -> "Treasurer":
    from .services import Treasurer

    return Treasurer()
