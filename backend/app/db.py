"""Storage boundary for the MVP.

The demo uses process-local storage so it runs without setup; this module is the
single seam to replace with PostgreSQL repositories in the next milestone.
"""

from .services import Treasurer

treasurer = Treasurer()

