"""
Session class and login/login by moodle function
"""

from __future__ import annotations

import json
import re
import atexit
from typing_extensions import Optional
import warnings
import httpx
import asyncio

from typing import Literal, Any
from datetime import datetime
from dataclasses import dataclass, field

import dateparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from . import file, user, forum, blog, tag, calendar, course
from ..util import commons, exceptions


@dataclass
class Session:
    """
    Represents a login session
    """

    rq: httpx.AsyncClient

    _sesskey: str | None = None
    _file_client_id: str | None = None
    _file_item_id: str | None = None
    _user_id: int | None = None
    _user: user.User | None = None
    _username: str | None = None

    async def __aenter__(self):
        await self.assert_login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
        return False

    # --- Session/auth related methods ---
    @property
    def moodlesession(self):
        return self.rq.cookies.get("MoodleSession")

    @property
    async def is_signed_in(self):
        resp = await self.rq.get("https://vle.kegs.org.uk")
        return str(resp.url) != "https://vle.kegs.org.uk/login/index.php"

    @property
    async def sesskey(self):
        """Get the sesskey query parameter used in various functions. Webscraped from JS..."""
        if self._sesskey is None:
            pfx = "var M = {}; M.yui = {};\nM.pageloadstarttime = new Date();\nM.cfg = "

            resp = await self.rq.get("https://vle.kegs.org.uk/")
            soup = BeautifulSoup(resp.text, "html.parser")

            self._sesskey = None
            for script in soup.find_all("script"):
                text = script.text
                if '"sesskey":' in text:
                    i = text.find(pfx)
                    if i > -1:
                        i += len(pfx) - 1
                        data = commons.consume_json(text, i)

                        if isinstance(data, dict):
                            self._sesskey = data.get("sesskey")

        return self._sesskey

    async def connect_notifications(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[int] = None,
        newestfirst: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
        """
        Because KEGSNet messaging is disabled, this is mostly useless
        I can still work out what would be the response format from the moodle docs, but no point
        """
        if user_id is None:
            user_id = await self.user_id

        data = await self.webservice(
            "message_popup_get_popup_notifications",
            limit=limit,
            offset=offset,
            useridto=user_id,
            newestfirst=int(newestfirst),
        )

        assert isinstance(data, dict)
        return data["unreadcount"], data["notifications"]

    @property
    async def file_client_id(self):
        """Get the client id value used for file management"""
        if self._file_client_id is None:
            resp = await self.rq.get("https://vle.kegs.org.uk/user/files.php")
            soup = BeautifulSoup(resp.text, "html.parser")

            for div in soup.find_all("div", {"class": "filemanager w-100 fm-loading"}):
                self._file_client_id = div.attrs["id"].split("filemanager-")[1]

        return self._file_client_id

    @property
    async def connected_user(self) -> user.User:
        """Fetch the connected user to this session"""
        if not self._user:
            self._user = await self.connect_user_by_id(self.user_id)

        assert self._user
        return self._user

    @property
    async def file_item_id(self):
        """Fetch the item id value used for file management"""
        if self._file_item_id is None:
            resp = await self.rq.get("https://vle.kegs.org.uk/user/files.php")
            soup = BeautifulSoup(resp.text, "html.parser")
            elem = soup.find("input", {"id": "id_files_filemanager"})
            assert elem is not None
            self._file_item_id = elem.attrs.get("value")

        return self._file_item_id

    @property
    async def username(self):
        """Fetch the connected user's username"""
        if self._username is None:
            resp = await self.rq.get("https://vle.kegs.org.uk/login/index.php")
            soup = BeautifulSoup(resp.text, "html.parser")
            for alert_elem in soup.find_all(attrs={"role": "alert"}):
                alert = alert_elem.text

                username = commons.webscrape_value(
                    alert,
                    "You are already logged in as ",
                    ", you need to log out before logging in as different user.",
                )
                if username:
                    self._username = username
                    break

        return self._username

    @property
    async def user_id(self):
        """Fetch the connected user's user id"""
        if self._user_id is None:
            resp = await self.rq.get("https://vle.kegs.org.uk/")
            soup = BeautifulSoup(resp.text, "html.parser")

            urltag = soup.find("a", {"title": "View profile"})
            assert urltag is not None
            url = urltag.attrs["href"]

            parsed = parse_qs(urlparse(url).query)
            self._user_id = int(parsed["id"][0])

        return self._user_id

    async def assert_login(self):
        """Raise an error if there is no connected user"""
        assert await self.is_signed_in

    async def logout(self):
        """
        Send a logout request to KEGSNet. After this is called, the session is supposed to no longer function.
        :return: The response from KEGSNet
        """
        resp = await self.rq.get(
            "https://vle.kegs.org.uk/login/logout.php",
            params={"sesskey": await self.sesskey},
        )
        print(f"Logged out with status code {resp.status_code}")
        return resp

    # --- Connecting ---
    async def connect_user_by_id(self, _id: int) -> user.User:
        """Get a user by ID and attach this session object to it"""
        ret = user.User(_id, _session=self)
        await ret.update_from_id()
        return ret

    async def get_users(
        self,
        _id: int | list[int] | None = None,
        idnumber: int | list[int] | None = None,
        username: str | list[str] | None = None,
        email: str | list[str] | None = None,
    ):
        if _id:
            _field = "id"
            _value = _id
        elif idnumber:
            _field = "idnumber"
            _value = idnumber
        elif username:
            _field = "username"
            _value = username
        elif email:
            _field = "email"
            _value = email
        else:
            raise ValueError("Nothing to search by")

        if not isinstance(_value, list):
            _value = [_value]

        data = await self.webservice(
            "core_user_get_users_by_field", field=_field, values=_value
        )
        return data

    def connect_partial_user(self, **kwargs):
        """
        Connect to a user with given kwargs without any updating
        """
        return user.User(_session=self, **kwargs)

    async def connect_forum(self, _id: int) -> forum.Forum:
        """Get a forum by ID and attach this session object to it"""
        ret = forum.Forum(_id, _session=self)
        await ret.update_by_id()
        return ret

    async def connect_site_news(self):
        return await self.connect_forum(377)

    # --- Private Files ---
    async def _file_data(self, fp: str) -> dict:
        """Fetch the JSON response for private files in a given directory"""

        # Believe or not, KegsNet does actually have some JSON endpoints!
        return (
            await self.rq.post(
                "https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                params={"action": "list"},
                data={
                    "sesskey": self.sesskey,
                    "clientid": self.file_client_id,
                    "itemid": self.file_item_id,
                    "filepath": fp,
                },
            )
        ).json()

    async def files_in_dir(self, fp: str) -> list[file.File]:
        """Fetch files in a given directory"""
        data = (await self._file_data(fp))["list"]
        files = []
        for file_data in data:
            files.append(file.File.from_json(file_data, self))
        return files

    @property
    async def files(self):
        """Fetch the files in the root directory"""
        return await self.files_in_dir("/")

    async def add_filepath(
        self, fp: str, data: bytes, author: str = "", _license: str = "unknown"
    ):
        """
        Add file by path - infer file title and file path, e.g. foo/bar/baz.txt
        :param fp:
        :param data:
        :param author:
        :param _license:
        :return:
        """
        split = fp.split("/")
        fp = "/".join(split[:-1])
        await self.add_file(split[-1], data, author, _license, fp)

    async def add_file(
        self,
        title: str,
        data: bytes,
        author: str = "",
        _license: str = "unknown",
        fp: str = "/",
        save_changes: bool = True,
    ):
        """
        Make a POST request to add a new file to the given filepath


        NOTE: KEGSNet automatically removes slashes from the title. if you want to put the file in a subdirectory, add slashes in the `fp` parameter

        If the filename already exists, KEGSNet will automatically add a number on. e.g. foo.txt -> foo (1).txt

        :param title: file title
        :param data: file content (bytes)
        :param author: Author metadata. Defaults to ''
        :param _license: Given license. Defaults to 'unknown'
        :param fp: Directory path to add the file. Defaults to the root directory
        :param save_changes: Whether to save the change. Defaults to True
        """
        # Perhaps this method should take in a File object instead of title/data/author etc

        await self.rq.post(
            "https://vle.kegs.org.uk/repository/repository_ajax.php",
            params={"action": "upload"},
            data={
                "sesskey": await self.sesskey,
                "repo_id": 3,  # I'm not sure if it has to be 3
                "title": title,
                "author": author,
                "license": _license,
                "clientid": await self.file_client_id,
                "itemid": await self.file_item_id,
                "savepath": fp,
            },
            files={"repo_upload_file": data},
        )

        # Save changes
        if save_changes:
            await self.file_save_changes()

    async def file_save_changes(self):
        """
        Tell kegsnet to save our changes to our files
        """
        await self.rq.post(
            "https://vle.kegs.org.uk/user/files.php",
            data={
                "returnurl": "https://vle.kegs.org.uk/user/files.php",
                "sesskey": await self.sesskey,
                "files_filemanager": await self.file_item_id,
                "_qf__user_files_form": 1,
                "submitbutton": "Save changes",
            },
        )

    @property
    async def file_zip(self) -> bytes:
        """
        Returns bytes of your files as a zip archive
        """
        url = (
            await self.rq.post(
                "https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                params={"action": "downloaddir"},
                data={
                    "sesskey": await self.sesskey,
                    "client_id": await self.file_client_id,
                    "filepath": "/",
                    "itemid": await self.file_item_id,
                },
            )
        ).json()["fileurl"]

        return (await self.rq.get(url)).content

    # --- Blogs ---
    def _find_blog_entires(self, soup: BeautifulSoup) -> list[blog.Entry]:
        entries = []
        main_div = soup.find("div", {"role": "main"})
        assert main_div is not None
        for div in main_div.find_all("div"):
            raw_id = div.attrs.get("id", "")

            if re.match(r"b\d*", raw_id):
                entries.append(blog.Entry(_session=self))
                entries[-1].update_from_div(div)

        return entries

    async def connect_user_blog_entries(
        self, userid: Optional[int] = None, *, limit: int = 10, offset: int = 0
    ) -> list[blog.Entry]:
        warnings.warn(
            "This will be deprecated soon. Try to use connect_blog_entries instead"
        )
        if userid is None:
            userid = await self.user_id

        entries = []
        for page, _ in zip(*commons.generate_page_range(limit, offset, 10, 0)):
            resp = await self.rq.get(
                "https://vle.kegs.org.uk/blog/index.php",
                params={"blogpage": page, "userid": userid},
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            entries += self._find_blog_entires(soup)

        return entries

    async def connect_blog_entries(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        # search filters
        _tag: Optional[tag.Tag] = None,
        _course: Optional[course.Course] = None,
        _user: Optional[user.User] = None,
        tagname: Optional[str] = None,
        tagid: Optional[int] = None,
        userid: Optional[int] = None,
        cmid: Optional[int] = None,  # idk what this one is
        entryid: Optional[int] = None,
        groupid: Optional[int] = None,
        courseid: Optional[int] = None,
        search: Optional[str] = None,
    ):
        if offset != 0:
            warnings.warn(
                "offset+limit -> page+perpage conversion has not been made yet! Offset will be ignored",
                category=exceptions.UnimplementedWarning,
            )

        filters = []

        def add_filter(name: str, value):
            if value is not None:
                filters.append({"name": name, "value": value})

        if _tag:
            tagid = _tag.id
        if _user:
            userid = _user.id
        if _course:
            courseid = _course.id

        add_filter("tag", tagname)
        add_filter("tagid", tagid)
        add_filter("userid", userid)
        add_filter("cmid", cmid)
        add_filter("entryid", entryid)
        add_filter("groupid", groupid)
        add_filter("courseid", courseid)
        add_filter("search", search)

        data = await self.webservice(
            "core_blog_get_entries", page=0, perpage=limit, filters=filters
        )

        return [
            blog.Entry.from_json(entry_data, self) for entry_data in data["entries"]
        ]

    async def connect_blog_entry_by_id(self, _id: int):
        entry = blog.Entry(id=_id, _session=self)
        await entry.update_from_id()
        return entry

    # --- Tags ---

    async def connect_tag_by_name(self, name: str) -> tag.Tag:
        _tag = tag.Tag(name, _session=self)
        await _tag.update()
        return _tag

    async def connect_tag_by_id(self, _id: int) -> tag.Tag:
        _tag = tag.Tag(id=_id, _session=self)
        await _tag.update()
        return _tag

    # --- Calendar ---

    async def connect_calendar(
        self,
        view_type: Literal["month", "day", "upcoming"] = "day",
        _time: int | float | datetime | None = None,
        _course: int | str | course.Course | None = None,
    ):
        if isinstance(_time, datetime):
            _time = _time.timestamp()

        if isinstance(_course, course.Course):
            _course = _course.id

        resp = await self.rq.get(
            "https://vle.kegs.org.uk/calendar/view.php",
            params={"view": view_type, "time": _time, "course": _course},
        )
        ret = calendar.Calendar(_sess=self)

        soup = BeautifulSoup(resp.text, "html.parser")
        div = soup.find("div", {"class": "calendarwrapper"})

        if view_type == "month":
            ...
        elif view_type in ("day", "upcoming"):
            assert div is not None
            evlist = div.find("div", {"class": "eventlist"})
            for event_div in evlist.find_all("div", {"data-type": "event"}):
                cal_event = calendar.Event(_sess=self)

                head = event_div.find(
                    "div", {"class": "box card-header clearfix calendar_event_user"}
                )

                cal_event.title = head.text.strip()

                body = event_div.find("div", {"class": "description card-body"})

                for row in body.find_all("div", {"class": "row"}):
                    row_type = row.find("i").get("title")

                    row_text = row.text.strip()
                    match row_type:
                        case "When":
                            _date = dateparser.parse(row_text)
                            assert _date is not None
                            cal_event.date = _date
                        case "Event type":
                            cal_event.type = row_text

                        case "Location":
                            cal_event.location = row_text

                        case "Description":
                            cal_event.description = row_text

                        case _:
                            warnings.warn(
                                f"Did not recognise calendar row type: {row_type!r} - report this on github: https://github.com/BigPotatoPizzaHey/kegscraper"
                            )
                ret.events.append(cal_event)

        return ret

    # -- Courses -- #
    async def connect_recent_courses(self, limit: int = 10, offset: int = 0):
        data = await self.webservice(
            "core_course_get_recent_courses", limit=limit, offset=offset
        )
        return [course.Course.from_json(course_data) for course_data in data]

    async def webservice(self, name, /, **args):
        """
        Directly interact with the webservice api
        :param name:methodname of webservice api, e.g. core_course_search_courses
        :param args:args to send to webservice api
        :return:
        """
        data = (
            await self.rq.post(
                "https://vle.kegs.org.uk/lib/ajax/service.php",
                params={"sesskey": await self.sesskey},  # "info": name
                json=[{"methodname": name, "args": args}],
            )
        ).json()

        skip = False
        if isinstance(data, dict):
            skip = "error" in data

        if not skip:
            data = data[0]

        if data["error"]:
            try:
                raise exceptions.WebServiceError(
                    f"{data['exception']['errorcode']!r}: {data['exception']['message']!r}"
                )
            except KeyError:
                try:
                    raise exceptions.WebServiceError(
                        f"{data['errorcode']!r}: {data['error']!r}"
                    )
                except KeyError:
                    raise exceptions.WebServiceError(f"Error: {data}")

        return data["data"]

    async def search_courses(self, query: str):
        data = await self.webservice(
            "core_course_search_courses", criterianame="tagid", criteriavalue=query
        )
        return data

    async def connect_enrolled_courses(
        self,
        classification: Literal["future", "inprogress", "past"] = "inprogress",
        limit: int = 9999,
        offset: int = 0,
    ):
        data = await self.webservice(
            "core_course_get_enrolled_courses_by_timeline_classification",
            classification=classification,
            limit=limit,
            offset=offset,
        )
        return data


# --- * ---


async def login(username: str, password: str) -> Session:
    """
    Login to kegsnet with a username and password
    :param username: Your username. Same as your email without '@kegs.org.uk'
    :param password: Your email password
    :return: a new session
    """

    rq = httpx.AsyncClient(headers=commons.headers.copy(), follow_redirects=True)

    resp = await rq.get("https://vle.kegs.org.uk/login/index.php")

    inputs = commons.eval_inputs(BeautifulSoup(resp.text, "html.parser"))
    inputs["username"] = username
    inputs["password"] = password
    # inputs["anchor"] = None

    await rq.post("https://vle.kegs.org.uk/login/index.php", data=inputs)

    return Session(rq=rq)


async def login_by_moodle(moodle_cookie: str) -> Session:
    """
    Login to kegsnet with just a moodle cookie (basically a session id)
    :param moodle_cookie: The MoodleSession cookie (see in the application/storage tab of your browser devtools when you log in)
    :return: A new session
    """
    rq = httpx.AsyncClient(
        cookies={"MoodleSession": moodle_cookie}, follow_redirects=True
    )

    try:
        return Session(rq=rq)
    except requests.exceptions.TooManyRedirects:
        raise ValueError(
            f"The moodle cookie {moodle_cookie!r} may be invalid/outdated."
        )
