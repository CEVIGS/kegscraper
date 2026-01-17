"""
Timetable Dataclasses for bromcom
"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing_extensions import Optional

from ..util import commons

from . import session


@dataclass
class WeekDate:
    """
    A dataclass representing a start of a week to be used with the bromcom timetable.
    """

    term_i: int
    week_i: int
    date: datetime
    _sess: Optional[session.Session] = None


@dataclass
class Lesson:
    """
    A dataclass representing a lesson in the bromcom timetable
    """

    period: Optional[str]
    subject: Optional[str]
    class_name: Optional[str]
    room: Optional[str]
    teacher: Optional[str]
    teacher_id: Optional[int]
    # ^^ I am unaware of any use. Perhaps if they have the same name
    week_id: Optional[int]
    # ^^ Seems to be that the only use is to differentiate week a/b?

    start: Optional[datetime]
    end: Optional[datetime]

    color: Optional[str] = None

    _sess: Optional[session.Session] = None
    week_a_b: Optional[str] = None

    @property
    def weekday(self):
        if self.start is None:
            return None
        return self.start.strftime("%A")

    # @property
    # def week_a_b(self):
    #     return "ba"[self.week_id % 2]


def get_mode_timetable(_timetable: list[Lesson]) -> dict[str, dict[str, Lesson]]:
    def find_lessons(
        _period: Optional[str] = None, day_name: Optional[str] = None
    ) -> list[Lesson]:
        ret = []
        for _lesson in _timetable:
            if _lesson.period == _period or _period is None:
                assert _lesson.start is not None
                if _lesson.start.strftime("%A") == day_name or day_name is None:
                    ret.append(_lesson)
        return ret

    periods = []
    for lesson in _timetable:
        if lesson.period in periods:
            break
        periods.append(lesson.period)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    result = {}

    for weekday in weekdays:
        result[weekday] = {}
        for period in periods:
            lessons = find_lessons(period, weekday)
            result[weekday][period] = commons.get_mode(lessons, no_dunder=True)

    return result

