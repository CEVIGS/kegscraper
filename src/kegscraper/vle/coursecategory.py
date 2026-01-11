from __future__ import annotations

from dataclasses import dataclass

from . import session

@dataclass
class CourseCategory:
    name: str = None # e.g. 'Chemistry Y9-11'

    _sess: session.Session = None