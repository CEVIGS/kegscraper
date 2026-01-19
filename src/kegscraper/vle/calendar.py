from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing_extensions import Any, Self, Optional

import dateparser
from bs4 import PageElement, BeautifulSoup

from . import session, user, tag
from ..util import commons, exceptions


@dataclass
class Event:
    _sess: session.Session

    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None

    date: Optional[datetime] = None


@dataclass
class Calendar:
    """
    An instance of a calendar widget that KEGSNet can give
    """

    _sess: session.Session
    events: list[Event] = field(default_factory=list)
