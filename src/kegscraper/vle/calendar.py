from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Any, Self

import dateparser
from bs4 import PageElement, BeautifulSoup

from . import session, user, tag
from ..util import commons, exceptions


@dataclass
class Event:
    title: str = None
    description: str = None
    location: str = None
    type: str = None

    date: datetime = None

    _sess: session.Session = None

@dataclass
class Calendar:
    """
    An instance of a calendar widget that KEGSNet can give
    """
    events: list[Event] = field(default_factory=list)

    _sess: session.Session = None
