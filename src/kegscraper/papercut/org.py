from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import session

@dataclass
class Organisation:
    pages_graph: list[int] = None

    trees: float = None
    co2: int = None
    energy: float = None
    since: datetime = None

    sess: session.Session = None
