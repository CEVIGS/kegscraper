"""
Timetable Dataclasses for bromcom
"""
from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass

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
    _sess: session.Session = None

@dataclass
class Lesson:
    """
    A dataclass representing a lesson in the bromcom timetable
    """
    period: str
    subject: str
    class_name: str
    room: str
    teacher: str
    teacher_id: int
    # ^^ I am unaware of any use. Perhaps if they have the same name
    week_id: int
    # ^^ Seems to be that the only use is to differentiate week a/b?

    start: datetime
    end: datetime

    color: str = None

    _sess: session.Session = None
    week_a_b: str = None

    @property
    def weekday(self):
        return self.start.strftime("%A")

    # @property
    # def week_a_b(self):
    #     return "ba"[self.week_id % 2]

def get_mode_timetable(_timetable: list[Lesson]) -> dict[str, dict[str, Lesson]]:
    def find_lessons(_period: str = None, day_name: str = None) -> list[Lesson]:
        ret = []
        for _lesson in _timetable:
            if _lesson.period == _period or _period is None:
                if _lesson.start.strftime("%A") == day_name or day_name is None:
                    ret.append(_lesson)
        return ret

    periods = []
    for lesson in _timetable:
        if lesson.period in periods:
            break
        periods.append(lesson.period)

    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    result = {}

    for weekday in weekdays:
        result[weekday] = {}
        for period in periods:
            lessons = find_lessons(period, weekday)
            result[weekday][period] = commons.get_mode(lessons, no_dunder=True)

    return result