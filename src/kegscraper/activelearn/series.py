from __future__ import annotations

from dataclasses import dataclass, field, InitVar

from . import session

@dataclass
class Subject:
    name: str = None
    short_name: str = field(repr=False, default=None)

    image_url: str = None

    _session: session.Session = field(repr=False, default=None)

@dataclass
class Series:
    name: str = None
    id: int = None
    subject: Subject = None

    _session: session.Session = field(repr=False, default=None)

    subject_name: InitVar[str] = None
    subject_short_name: InitVar[str] = None

    def __post_init__(self, subject_name: str, subject_short_name: str):
        if not self.subject:
            self.subject = Subject()

        self.subject.name = subject_name
        self.subject.short_name = subject_short_name

        self.subject._session = self._session

    def get_books(self):
        self._session.page.goto(f"https://www.pearsonactivelearn.com/app/library/series/view/{self.id}#/studentbooks")

        self._session.page.locator(selector:="ul .tab-book-list.clearfix.studentbooks]").wait_for()
        print(self._session.page.query_selector(selector))