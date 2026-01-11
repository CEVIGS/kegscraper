"""
Module for reading the event list pdf at https://www.kegs.org.uk/eventsPDF.cfm
"""
from typing import Final
from io import BytesIO
import re

import dateparser
from pypdf import PdfReader

from .events import ATCEvent

MONTHS: Final[tuple[str, str, str, str, str, str, str, str, str, str, str, str]] = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December")

# noinspection PyTypeChecker
re_mnth = '|'.join(map(str.upper, MONTHS))


def read(pdf_data: bytes) -> list[ATCEvent]:
    """
    Parse a KEGS Events pdf into a list of events. Does not validate the pdf.
    :param pdf_data: The pdf as bytes
    :return: a list of events
    """
    pdf = PdfReader(BytesIO(pdf_data))
    text = ''
    for page in pdf.pages:
        text += page.extract_text() + '\n'

    events: list[ATCEvent] = []
    year = None
    for line in text.split('\n'):
        line: str
        line = line.strip()

        if line == "KEGS Events":
            # It's the top line
            ...

        elif m := re.match(fr"({re_mnth}) \d\d\d\d", line):
            # In format: {MONTH} {yyyy}
            m = m.group()

            # We can ignore the month, but we can't get the year data from anywhere else
            year = m[-4:]

        elif line == '':
            # Ignore blank lines
            continue

        else:
            # We can assume that the rest are just events

            # Format: [Day name in titlecase], [day #] [1st 3 chars of month] [All Day | hh:mm - hh:mm] [Description]
            split = line.split(', ')
            day_name, rest = split[0], ', '.join(split[1:])

            split = rest.split(' ')
            day, month, rest = split[0], split[1], ' '.join(split[2:])

            for full_month in MONTHS:
                if full_month.startswith(month):
                    month = full_month
            month = MONTHS.index(month) + 1

            all_day = rest.startswith("All Day ")
            if all_day:
                title = rest[len("All Day "):]
                start, end = '', ''
            else:
                # Some time in format: hh:mm
                split = rest.split(' ')

                start, end, title = split[0], split[2], ' '.join(split[3:])

            start_date = dateparser.parse(f"{day}/{month}/{year} {start}")
            end_date = dateparser.parse(f"{day}/{month}/{year} {end}")

            events.append(ATCEvent(start_date, end_date, title=title, all_day=all_day))

    return events
