from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing_extensions import Optional

from bs4 import BeautifulSoup

from . import session, coursecategory
from ..util import exceptions


@dataclass
class Course:
    _sess: session.Session

    id: Optional[int] = None
    display_name: Optional[str] = None  # == fullname == fullnamedisplay
    name: Optional[str] = None  # == shortname
    summary: Optional[BeautifulSoup] = (
        None  # summaryformat is always == 1 for me. maybe that affects this
    )

    start_time: Optional[datetime] = None
    end_time: datetime | None = None  # set to none if the value is 0
    access_time: Optional[datetime] = None

    category: Optional[coursecategory.CourseCategory] = None

    image: Optional[str] = field(default=None, repr=False)

    hidden: Optional[bool] = None

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
    def from_json(cls, data: dict, sess: session.Session):
        if data["fullname"] != data["fullnamedisplay"]:
            warnings.warn(
                f"Please report to github, fullname != fullnamedisplay: {data}",
                category=exceptions.UnimplementedWarning,
            )

        return cls(
            _sess=sess,
            id=data["id"],
            display_name=data["fullnamedisplay"],
            name=data["shortname"],
            summary=BeautifulSoup(data["summary"], "html.parser"),
            start_time=datetime.fromtimestamp(data["startdate"]),
            end_time=(
                datetime.fromtimestamp(data["enddate"])
                if data.get("endate", 0) != 0
                else None
            ),
            access_time=datetime.fromtimestamp(data["timeaccess"]),
            image=data["courseimage"],
            hidden=data["hidden"],
            category=coursecategory.CourseCategory(
                _sess=sess, name=data["coursecategory"]
            ),
        )
