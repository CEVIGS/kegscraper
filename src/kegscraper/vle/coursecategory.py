from __future__ import annotations

from dataclasses import dataclass
from typing_extensions import Optional

from . import session


@dataclass
class CourseCategory:
    _sess: session.Session
    name: Optional[str] = None  # e.g. 'Chemistry Y9-11'

