from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup

from . import session, coursecategory
from ..util import exceptions


@dataclass
class Course:
    id: int = None
    display_name: str = None  # == fullname == fullnamedisplay
    name: str = None  # == shortname
    summary: BeautifulSoup = None  # summaryformat is always == 1 for me. maybe that affects this

    start_time: datetime = None
    end_time: datetime | None = None  # set to none if the value is 0
    access_time: datetime = None

    category: coursecategory.CourseCategory = None

    image: str = field(default=None, repr=False)

    hidden: bool = None

    _sess: session.Session = None

    """
    Should these attrs be ignored?:
    fullname
    viewurl
    progress
    hasprogress
    isfavourite
    showshortname
    """

    @classmethod
    def from_json(cls, data: dict[str, str | bool | int], sess: session.Session = None):
        if data["fullname"] != data["fullnamedisplay"]:
            warnings.warn(f"Please report to github, fullname != fullnamedisplay: {data}",
                          category=exceptions.UnimplementedWarning)

        return cls(
            _sess=sess,
            id=data["id"],
            display_name=data["fullnamedisplay"],
            name=data["shortname"],
            summary=BeautifulSoup(data["summary"], "html.parser"),
            start_time=datetime.fromtimestamp(data["startdate"]),
            end_time=datetime.fromtimestamp(data["enddate"]) if data.get("endate", 0) != 0 else None,
            access_time=datetime.fromtimestamp(data["timeaccess"]),
            image=data["courseimage"],
            hidden=data["hidden"],
            category=coursecategory.CourseCategory(_sess=sess,
                                                   name=data["coursecategory"])

        )
