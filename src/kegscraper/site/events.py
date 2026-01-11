import json

import requests
from datetime import datetime
from dataclasses import dataclass, field
import dateparser

from typing_extensions import deprecated

from bs4 import BeautifulSoup, SoupStrainer
from ..util import commons


@dataclass
class ATCEvent:
    # stands for 'Add-to-calendar' event
    """
    Represents a calendar event managed by the atc api
    """
    start: datetime
    end: datetime

    timezone: str = None  # Maybe there is a way to parse this? (e.g. 'Europe/London')

    title: str = None
    description: str = None
    location: str = None
    organiser: str = None

    all_day: bool = False
    """Attribute storing if it is an all-day event for compatability with the KEGS Events PDF"""

    @classmethod
    def from_data(cls, data: dict[str, str]):
        """Load an event from a dictionary of data from the atc api"""
        return cls(
            dateparser.parse(data.get("atc_date_start")),
            dateparser.parse(data.get("atc_date_end")),

            data.get("atc_timezone"),
            data.get("atc_title"),
            data.get("atc_description"),
            data.get("atc_location"),
            data.get("atc_organizer"),
        )

    def __repr__(self):
        return f"Event<{self.title!r} {commons.to_dformat(self.start, sep='/')} - {commons.to_dformat(self.end, sep='/')}>"


@dataclass
class CalendarEvent:
    """
    Represents a calendar event stored on the kegs main website
    """
    id: int

    code_name: str = '_'  # Used for fetching url, but doesn't actually matter

    _event_data: ATCEvent = field(repr=False, default=None)

    @property
    def url(self) -> str:
        """Get a link to the calendar event. This will time out at some point"""
        return f"https://kegs.org.uk/{self.code_name}/{self.id}.html"

    @property
    def event_data(self) -> ATCEvent:
        """Get the actual data for the calendar event, and return as an ATCEvent object"""
        if self._event_data is None:
            text = commons.REQ.get(self.url).text
            soup = BeautifulSoup(text, "html.parser")

            atc_btn = soup.find("span", {"class": "addtocalendar"})
            event_var = atc_btn.find("var", {"class": "atc_event"})

            data = {}
            for var in event_var.find_all("var"):
                data[' '.join(var["class"])] = var.text

            self._event_data = ATCEvent.from_data(data)

        return self._event_data

@deprecated("This endpoint has been removed")
def get_events_pdf() -> bytes:
    """
    Fetch the KEGS event list pdf as bytes
    """
    return commons.REQ.get("https://www.kegs.org.uk/eventsPDF.cfm").content

@deprecated("This endpoint has been removed")
def get_calendar_page(date: datetime | str = None, by: str = "MONTH") -> list[CalendarEvent]:
    """
    Fetch the list of calendar events corresponding the page on the calendar
    :param date: Date to fetch data around
    :param by: Event fetching mode: either 'WEEK' or 'MONTH'
    :return: A list of CalendarEvent objects
    """
    if date is None:
        date = datetime.today()

    if isinstance(date, datetime):
        # Maybe edit commons.to_dformat
        date = f"{str(date.day).zfill(2)}/{str(date.month).zfill(2)}/{date.year}"

    by = by.upper()
    response = commons.REQ.get("https://www.kegs.org.uk/plugins/cfc/bycontentid/website/calendar.cfc",
                            params={
                                "method": "fncDisplayMobile",
                                "returnFormat": "json",  # It doesn't return JSON though...

                                "_cf_ajaxproxytoken": "670A99ACD5D7DDD0",  # This seems to be consistent across sessions
                                "_cf_clientid": "B08044EF38BAB77125840DD9A5ADFCDF",  # Also consistent

                                "_cf_nodebug": True,
                                "_cf_nocache": True,
                                "_cf_rc": 0,

                                "argumentCollection": json.dumps({
                                    "mobileMode": by,
                                    "mobileDate": date,
                                    "mobileHide": 0,
                                    "mobileCat": 2693,
                                    "mobileSearch": "search",
                                    "mobileType": "all",
                                    "mobileDept": "all"
                                })
                            })

    soup = BeautifulSoup(response.text, "html.parser", parse_only=SoupStrainer("a"))

    partial_events = []
    for anchor in soup.find_all("a"):
        if "href" in anchor.attrs:
            href = '"' + anchor["href"] + '"'
            href: str = json.loads(json.loads(href))  # Yeah, it seems to be double json encoded

            _, name, cid = href.split('/')

            cid = commons.keep_chrs(cid, cls=int)

            partial_events.append(CalendarEvent(
                cid, code_name=name
            ))

    return partial_events
