"""
Session class and login function. (most bromcom functionality)
"""

from __future__ import annotations

import dateparser
import httpx

from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing_extensions import Optional, Any
from base64 import b64decode
from bs4 import BeautifulSoup, SoupStrainer

from . import timetable
from ..util import exceptions, commons


@dataclass
class Session:
    rq: httpx.AsyncClient
    username: str

    _name: Optional[str] = None
    _timetable_weeks: Optional[list[timetable.WeekDate]] = None

    def __repr__(self):
        # repr can't be async. this is problematic
        return f"Session for {self.username}"

    async def logout(self) -> httpx.Response:
        """
        Send a logout request to bromcom. After this is called, the session will no longer function.
        :return: The response from bromcom
        """
        return await self.rq.get("https://www.bromcomvle.com/Auth/Logout")

    # --- Account settings ---
    async def set_color_preference(
        self, *, name: str = "Theme", value: str = "default"
    ):
        """
        Set a color preference request to bromcom. Might not work yet
        """
        return await self.rq.post(
            "https://www.bromcomvle.com/AccountSettings/SaveColorPreference",
            json={"Name": name, "Value": value},
        )

    @property
    async def email(self) -> Optional[str]:
        """
        Fetch the user email from the account settings page
        """
        resp = await self.rq.get("https://www.bromcomvle.com/AccountSettings")
        inps = commons.eval_inputs(BeautifulSoup(resp.text, "html.parser"))
        return inps.get("EmailAddress")

    @property
    async def school_contact_details(self) -> dict[str, str | Any]:
        """
        Fetch the school contact details as a key:value table from the hidden drop-down menu
        """
        resp = await self.rq.get("https://www.bromcomvle.com/Home/Dashboard")
        soup = BeautifulSoup(resp.text, "html.parser")

        conn_anchor = soup.find("a", {"title": "Contact School"})
        assert conn_anchor is not None
        table = conn_anchor.parent.find("table")

        data = {}
        for tr in table.find_all("tr"):
            tr_data = []
            for i, td in enumerate(tr.find_all("td")):
                text: str = td.text
                if i == 0:
                    continue

                elif text.endswith(":"):
                    # Trim off colon
                    text = text[:-1]

                tr_data.append(text)

            if len(tr_data) == 2:
                # Only add stuff that can be made into a dict
                data[tr_data[0]] = tr_data[1]

        return data

    @property
    async def name(self) -> Optional[str]:
        """
        Fetch the student name (not username) from the dashboard page
        """
        if self._name is None:
            resp = await self.rq.get("https://www.bromcomvle.com/Home/Dashboard")
            soup = BeautifulSoup(
                resp.text, "html.parser", parse_only=SoupStrainer("span")
            )

            message = soup.find("span", {"id": "UsernameLabel"})
            if message is None:
                raise exceptions.NotFound(
                    f"Could not find welcome message! Response: {resp.text}"
                )

            self._name = message.text.strip()
            if not isinstance(self._name, str):
                self._name = None

        return self._name

    @property
    async def pfp(self) -> tuple[bytes, str]:
        """
        Fetch the user's corresponding profile picture as bytes, as well as a fileext
        """
        resp = await self.rq.get(
            "https://www.bromcomvle.com/AccountSettings/GetPersonPhoto"
        )
        return commons.resp_to_file(resp, ".jpg")

    @property
    async def school_photo(self) -> tuple[bytes, str]:
        """
        Fetch the school's corresponding photo as bytes
        """
        resp = await self.rq.get(
            "https://www.bromcomvle.com/AccountSettings/GetSchoolPhoto"
        )
        return commons.resp_to_file(resp, ".jpg")

    # --- Timetable methods ---
    async def get_timetable_list(
        self,
        start_date: datetime | timetable.WeekDate | None = None,
        end_date: datetime | timetable.WeekDate | None = None,
        w_a_b: str | None = None,
    ) -> list[timetable.Lesson]:
        """
        Fetch the user's timetable starting at a corresponding week and ending on another, as a list of Lesson objects
        :param w_a_b: week a or b on start date
        :param start_date: The start date given to bromcom. Can be a datetime or a WeekDate object. Defaults to the latest valid week.
        :param end_date: The end date fiven to bromcom. Defaults to a week ahead of the start date.
        :return: A list of lesson objects, each with a period #, subject name, class name, room name etc.
        """

        if isinstance(start_date, timetable.WeekDate):
            start_date = start_date.date

        if isinstance(end_date, timetable.WeekDate):
            end_date = end_date.date

        if start_date is None:
            cw = await self.current_week
            assert cw is not None, "Could not find current week"
            start_date = cw.date

        if end_date is None:
            end_date = start_date + timedelta(weeks=1)

        if w_a_b is None:
            tt_week = await self.get_tt_week(start_date)
            assert tt_week is not None, f"Could not find tt_week for {start_date}"
            wab_offset = (await self.timetable_weeks).index(tt_week) % 2
        else:
            wab_offset = "ab".index(w_a_b)

        resp = await self.rq.get(
            "https://www.bromcomvle.com/Timetable/GetTimeTable",
            params={
                "WeekStartDate": commons.to_dformat(start_date),
                "weekEndDate": commons.to_dformat(end_date),
                "type": 1,
            },
        )
        data = resp.json()["table"]

        lessons = []
        for lesson_data in data:
            # lesson_data: dict[str, str | int]
            lesson_data: dict[str, Any]

            lesson_start_date = datetime.fromisoformat(lesson_data["startDate"])
            lessons.append(
                timetable.Lesson(
                    lesson_data.get("periods"),
                    lesson_data.get("subject"),
                    lesson_data.get("class"),
                    lesson_data.get("room"),
                    lesson_data.get("teacherName"),
                    lesson_data.get("teacherID"),
                    lesson_data.get("weekID"),
                    lesson_start_date,
                    datetime.fromisoformat(lesson_data["endDate"]),
                    color=lesson_data.get("subjectColour"),
                    _sess=self,
                    week_a_b="ab"[
                        (
                            (await self.get_tt_week_idx(lesson_start_date))
                            - (await self.get_tt_week_idx(start_date))
                            + wab_offset
                        )
                        % 2
                    ],
                )
            )
        return lessons

    async def get_weeks_a_b(
        self, delta: int = 5
    ) -> tuple[list[timetable.Lesson], list[timetable.Lesson]]:
        """
        Get 2 lists of lessons (weeka, weekb), generated `delta` weeks back and forth from the current week
        :param delta: number of weeks before and after to measure
        :return:
        """
        idx = await self.current_week_idx

        weeks0: list[timetable.Lesson] = []
        weeks1: list[timetable.Lesson] = []

        for i in range(idx - delta, idx + delta):
            if not 0 <= i < len(await self.timetable_weeks):
                continue

            weeks = await self.timetable_weeks
            _timetable = await self.get_timetable_list(weeks[i])

            for lesson in _timetable:
                if lesson.week_a_b == "a":
                    weeks0.append(lesson)
                else:
                    weeks1.append(lesson)

        return weeks0, weeks1

    async def get_mode_timetables(self, delta: int = 5):
        """
        Infer the base timetable. Look over multiple weeks to avoid being tripped up by pshe, or Comp Room lessons etc.
        :param delta: # of weeks forward/back to look at
        :return: a dictionary of a dictionary of a dictionary of lessons
        """
        a, b = await self.get_weeks_a_b(delta)
        return {
            "a": timetable.get_mode_timetable(a),
            "b": timetable.get_mode_timetable(b),
        }

    @property
    async def timetable_weeks(self) -> list[timetable.WeekDate]:
        """
        Fetch a list of valid weeks in the user's timetable
        :return: A list of WeekDate objects, representing the start of each week, also containing a term and week index.
        """
        if self._timetable_weeks is None:
            self._timetable_weeks = []

            resp = await self.rq.get("https://www.bromcomvle.com/Timetable")
            soup = BeautifulSoup(resp.text, "html.parser")

            date_selector = soup.find("select", {"id": "WeekStartDate"})
            assert date_selector is not None

            for option in date_selector.find_all("option"):
                value = dateparser.parse(option.attrs.get("value"))
                assert value is not None, f"Failed to parse date"
                text = option.text

                term, week, _ = text.split(" - ")
                term = commons.webscrape_section(term, "Term ", "", cls=int)
                week = commons.webscrape_section(week, "Week ", "", cls=int)

                self._timetable_weeks.append(timetable.WeekDate(term, week, value))

        return self._timetable_weeks

    async def get_tt_week(self, _dtime: datetime) -> timetable.WeekDate | None:
        """
        Gets the timetable week by datetime
        """
        prev = None
        for wdate in await self.timetable_weeks:
            if wdate.date > _dtime:
                return prev
            prev = wdate

    @property
    async def current_week(self) -> timetable.WeekDate | None:
        """
        Gets the current existing timetable week (will go to last school week during holidays)
        """
        return await self.get_tt_week(datetime.today())

    async def get_tt_week_idx(self, _dtime: datetime) -> int:
        """
        Gets the timetable week index by datetime
        """
        for i, wdate in enumerate(await self.timetable_weeks):
            if wdate.date > _dtime:
                return i
        return -1

    @property
    async def current_week_idx(self) -> int:
        return await self.get_tt_week_idx(datetime.today())

    # --- Attendance methods ---
    @property
    async def present_late_ratio(self) -> dict[str, int]:
        """
        Webscrape JSON inside JS inside HTML to get the present, late and other attendance type counts. i.e.:
        Returns a dictionary e.g.: {
        "Present (P)": 176,
        "Late (L)": 21
        }
        :return: A dictionary of attendance statuses and their counts
        """
        # Parse JSON inside of JS inside of HTML. Yeah....
        resp = await self.rq.get("https://www.bromcomvle.com/Attendance")
        soup = BeautifulSoup(resp.text, "html.parser")

        script_prf = "$(document).ready(function () {\r\n            var AttendanceChart = c3.generate({\r\n                bindto: '#AttendanceChart',\r\n"

        for script in soup.find_all("script", {"type": "text/javascript"}):
            text = script.text.strip()

            if script_prf in text:
                # Found correct js script. Now webscrape.
                text = text[text.find(script_prf) :]
                text = text[text.find("data: ") :]
                text = text[text.find("columns: [") + 9 :]

                data = commons.consume_json(text)
                assert isinstance(data, list)

                ret = {cat: count for cat, count in data}

                return ret

        return {}

    @property
    async def attendance_status(self):
        """
        Get the Status for the current day. (Uses the widget api)
        """
        return (
            await self.rq.get("https://www.bromcomvle.com/Home/GetAttendanceWidgetData")
        ).json()

    # --- Reports data ---

    @property
    async def reports_data(self) -> dict[str, list[dict[str, str]]]:
        """
        Fetch the report list (needs to be parsed)
        :return: A list of dictionaries representing reports. The filePath attribute can be used in the get_report method to fetch the report pdf as bytes
        """
        # Parse this later
        return (
            await self.rq.get("https://www.bromcomvle.com/Home/GetReportsWidgetData")
        ).json()

    async def get_report(
        self, filepath: str
    ) -> bytes:  # not possible to provide fileext because the endpoint is JSON
        """
        Get the report with the given 'filepath' as bytes
        :param filepath: The filePath attribute in the report data
        :return: The report data as bytes
        """
        # Get the data encoded in b64 encoded in JSON. Weird.
        resp = await self.rq.get(
            "https://www.bromcomvle.com/Report/GetReport",
            params={"filePath": filepath},
        )

        return b64decode(resp.json())

    # --- Exam data ---

    @property
    async def exam_data(self) -> list[dict[str, str]]:
        """
        Fetch the exam data from the widget api
        :return:
        """
        # Parse this
        return (
            await self.rq.get(
                "https://www.bromcomvle.com/Home/GetExamResultsWidgetData"
            )
        ).json()

    # --- Bookmarks data ---
    @property
    async def bookmarks_data(self) -> list[dict]:
        """
        Get the bookmarks list as a list of dictionaries (needs to be parsed)
        :return: list of dictionaries, each is a bookmark
        """
        # Parse this
        return (
            await self.rq.get("https://www.bromcomvle.com/Home/GetBookmarksWidgetData")
        ).json()

    # --- Homework data ---
    @property
    async def homework_data(self) -> list:
        """
        Fetch homework data using the widget api. I have no homework here so I am unable to parse this
        :return: A list of something
        """
        return (
            await self.rq.get("https://www.bromcomvle.com/Home/GetHomeworkWidgetData")
        ).json()


async def login(
    school_id: int,
    username: str,
    password: str,
    remember_me: bool = True,
    kwargs: Optional[dict] = None,
) -> Session:
    """
    Login to bromcom with a school id, username and password.
    :param school_id: KEGS school id (you provide it)
    :param username: Your username
    :param password: Your password
    :param remember_me: Option to 'remember me.' Defaults to True
    :return: A session representing your login
    """
    if kwargs is None:
        kwargs = {}
    rq = httpx.AsyncClient(headers=commons.headers.copy(), **kwargs)
    inputs = commons.eval_inputs(
        BeautifulSoup((await rq.get("https://www.bromcomvle.com/")).text, "html.parser")
    )

    inputs["schoolid"] = school_id
    inputs["username"] = username
    inputs["password"] = password
    inputs["rememberme"] = str(remember_me)
    resp = await rq.post(
        "https://www.bromcomvle.com/", data=inputs, follow_redirects=True
    )

    if resp.status_code != 200:
        if resp.status_code == 500:
            raise exceptions.ServerError(
                f"The bromcom server experienced some error when handling the login request (ERR 500). Response content: {resp.content}"
            )
        else:
            raise exceptions.Unauthorised(
                f"The provided details for {username} may be invalid. Status code: {resp.status_code} "
                f"Response content: {resp.content}"
            )

    return Session(rq=rq, username=username)
