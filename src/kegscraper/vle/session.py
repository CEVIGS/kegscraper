"""
Session class and login/login by moodle function
"""
from __future__ import annotations

import json
import re
import atexit
import warnings

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
    _sesskey: str | None = None
    _file_client_id: str | None = None
    _file_item_id: str | None = None
    _user_id: int | None = None
    _user: user.User | None = None
    _username: str | None = None

    rq: requests.Session = None

    def __post_init__(self):
        """Request handler (requests session object)"""

        self.assert_login()

        atexit.register(self.logout)

    # --- Session/auth related methods ---
    def unregister_logout(self):
        atexit.unregister(self.logout)

    @property
    def moodlesession(self):
        return self.rq.cookies.get("MoodleSession")

    @property
    def is_signed_in(self):
        return self.rq.get("https://vle.kegs.org.uk").url != "https://vle.kegs.org.uk/login/index.php"

    @property
    def sesskey(self):
        """Get the sesskey query parameter used in various functions. Webscraped from JS..."""
        if self._sesskey is None:
            pfx = "var M = {}; M.yui = {};\nM.pageloadstarttime = new Date();\nM.cfg = "

            response = self.rq.get("https://vle.kegs.org.uk/")
            soup = BeautifulSoup(response.text, "html.parser")

            self._sesskey = None
            for script in soup.find_all("script"):
                text = script.text
                if "\"sesskey\":" in text:
                    i = text.find(pfx)
                    if i > -1:
                        i += len(pfx) - 1
                        data = commons.consume_json(text, i)

                        if isinstance(data, dict):
                            self._sesskey = data.get("sesskey")

        return self._sesskey

    def connect_notifications(self, *, limit: int = 20, offset: int = 0,
                              user_id: int = None, newestfirst: bool = True) -> tuple[int, list[dict[str, Any]]]:
        """
        Because KEGSNet messaging is disabled, this is mostly useless
        I can still work out what would be the response format from the moodle docs, but no point
        """
        if user_id is None:
            user_id = self.user_id

        data = self.webservice("message_popup_get_popup_notifications",
                               limit=limit, offset=offset, useridto=user_id, newestfirst=int(newestfirst))

        return data["unreadcount"], data["notifications"]

    @property
    def file_client_id(self):
        """Get the client id value used for file management"""
        if self._file_client_id is None:
            response = self.rq.get("https://vle.kegs.org.uk/user/files.php")
            soup = BeautifulSoup(response.text, "html.parser")

            for div in soup.find_all("div", {"class": "filemanager w-100 fm-loading"}):
                self._file_client_id = div.attrs["id"].split("filemanager-")[1]

        return self._file_client_id

    @property
    def connected_user(self) -> user.User:
        """Fetch the connected user to this session"""
        if not self._user:
            self._user = self.connect_user_by_id(self.user_id)

        return self._user

    @property
    def file_item_id(self):
        """Fetch the item id value used for file management"""
        if self._file_item_id is None:
            response = self.rq.get("https://vle.kegs.org.uk/user/files.php")
            soup = BeautifulSoup(response.text, "html.parser")
            self._file_item_id = soup.find("input", {"id": "id_files_filemanager"}).attrs.get("value")

        return self._file_item_id

    @property
    def username(self):
        """Fetch the connected user's username"""
        if self._username is None:
            response = self.rq.get("https://vle.kegs.org.uk/login/index.php")
            soup = BeautifulSoup(response.text, "html.parser")
            for alert_elem in soup.find_all(attrs={"role": "alert"}):
                alert = alert_elem.text

                username = commons.webscrape_value(alert, "You are already logged in as ",
                                                   ", you need to log out before logging in as different user.")
                if username:
                    self._username = username
                    break

        return self._username

    @property
    def user_id(self):
        """Fetch the connected user's user id"""
        if self._user_id is None:
            response = self.rq.get("https://vle.kegs.org.uk/")
            soup = BeautifulSoup(response.text, "html.parser")

            url = soup.find("a", {"title": "View profile"}) \
                .attrs["href"]

            parsed = parse_qs(urlparse(url).query)
            self._user_id = int(parsed.get("id")[0])

        return self._user_id

    def assert_login(self):
        """Raise an error if there is no connected user"""
        assert self.is_signed_in

    def logout(self):
        """
        Send a logout request to KEGSNet. After this is called, the session is supposed to no longer function.
        :return: The response from KEGSNet
        """
        response = self.rq.get("https://vle.kegs.org.uk/login/logout.php",
                               params={"sesskey": self.sesskey})
        print(f"Logged out with status code {response.status_code}")
        return response

    # --- Connecting ---
    def connect_user_by_id(self, _id: int) -> user.User:
        """Get a user by ID and attach this session object to it"""
        ret = user.User(_id, _session=self)
        ret.update_from_id()
        return ret

    def get_users(self, _id: int | list[int] | None = None, idnumber: int | list[int] | None = None, username: str | list[str] | None = None, email: str | list[str] | None = None):
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

        data = self.webservice("core_user_get_users_by_field", field=_field, values=_value)
        return data

    def connect_partial_user(self, **kwargs):
        """
        Connect to a user with given kwargs without any updating
        """
        return user.User(_session=self, **kwargs)

    def connect_forum(self, _id: int) -> forum.Forum:
        """Get a forum by ID and attach this session object to it"""
        ret = forum.Forum(_id, _session=self)
        ret.update_by_id()
        return ret

    def connect_site_news(self):
        return self.connect_forum(377)

    # --- Private Files ---
    def _file_data(self, fp: str) -> dict:
        """Fetch the JSON response for private files in a given directory"""

        # Believe or not, KegsNet does actually have some JSON endpoints!
        return self.rq.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                            params={"action": "list"},
                            data={
                                "sesskey": self.sesskey,

                                "clientid": self.file_client_id,
                                "itemid": self.file_item_id,
                                "filepath": fp
                            }).json()

    def files_in_dir(self, fp: str) -> list[file.File]:
        """Fetch files in a given directory"""
        data = self._file_data(fp)["list"]
        files = []
        for file_data in data:
            files.append(file.File.from_json(file_data, self))
        return files

    @property
    def files(self):
        """Fetch the files in the root directory"""
        return self.files_in_dir('/')

    def add_filepath(self, fp: str, data: bytes, author: str = '', _license: str = "unknown"):
        """
        Add file by path - infer file title and file path, e.g. foo/bar/baz.txt
        :param fp:
        :param data:
        :param author:
        :param _license:
        :return:
        """
        split = fp.split('/')
        fp = '/'.join(split[:-1])
        self.add_file(split[-1], data, author, _license, fp)

    def add_file(self, title: str, data: bytes, author: str = '', _license: str = "unknown", fp: str = '/',
                 save_changes: bool = True):
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

        self.rq.post("https://vle.kegs.org.uk/repository/repository_ajax.php",
                     params={"action": "upload"},
                     data={
                         "sesskey": self.sesskey,
                         "repo_id": 3,  # I'm not sure if it has to be 3

                         "title": title,
                         "author": author,
                         "license": _license,

                         "clientid": self.file_client_id,
                         "itemid": self.file_item_id,
                         "savepath": fp
                     },
                     files={"repo_upload_file": data})

        # Save changes
        if save_changes:
            self.file_save_changes()

    def file_save_changes(self):
        """
        Tell kegsnet to save our changes to our files
        """
        self.rq.post("https://vle.kegs.org.uk/user/files.php",
                     data={"returnurl": "https://vle.kegs.org.uk/user/files.php",

                           "sesskey": self.sesskey,
                           "files_filemanager": self.file_item_id,
                           "_qf__user_files_form": 1,
                           "submitbutton": "Save changes"})

    @property
    def file_zip(self) -> bytes:
        """
        Returns bytes of your files as a zip archive
        """
        url = self.rq.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                           params={"action": "downloaddir"},
                           data={
                               "sesskey": self.sesskey,
                               "client_id": self.file_client_id,
                               "filepath": '/',
                               "itemid": self.file_item_id
                           }).json()["fileurl"]

        return self.rq.get(url).content

    # --- Blogs ---
    def _find_blog_entires(self, soup: BeautifulSoup) -> list[blog.Entry]:
        entries = []
        for div in soup.find("div", {"role": "main"}).find_all("div"):
            raw_id = div.attrs.get("id", '')

            if re.match(r"b\d*", raw_id):
                entries.append(blog.Entry(_session=self))
                entries[-1].update_from_div(div)

        return entries

    def connect_user_blog_entries(self, userid: int = None, *, limit: int = 10, offset: int = 0) -> list[blog.Entry]:
        warnings.warn("This will be deprecated soon. Try to use connect_blog_entries instead")
        if userid is None:
            userid = self.user_id

        entries = []
        for page, _ in zip(*commons.generate_page_range(limit, offset, 10, 0)):
            text = self.rq.get("https://vle.kegs.org.uk/blog/index.php",
                               params={
                                   "blogpage": page,
                                   "userid": userid
                               }).text
            soup = BeautifulSoup(text, "html.parser")
            entries += self._find_blog_entires(soup)

        return entries

    def connect_blog_entries(self, *, limit: int = 10, offset: int = 0,
                             # search filters
                             _tag: tag.Tag = None,
                             _course: course.Course = None,
                             _user: user.User = None,
                             tagname: str = None,
                             tagid: int = None,
                             userid: int = None,
                             cmid: int = None,  # idk what this one is
                             entryid: int = None,
                             groupid: int = None,
                             courseid: int = None,
                             search: str = None,
                             ):
        if offset != 0:
            warnings.warn("offset+limit -> page+perpage conversion has not been made yet! Offset will be ignored",
                          category=exceptions.UnimplementedWarning)

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

        data = self.webservice("core_blog_get_entries",
                               page=0, perpage=limit, filters=filters)

        return [blog.Entry.from_json(entry_data, self) for entry_data in data["entries"]]

    def connect_blog_entry_by_id(self, _id: int):
        entry = blog.Entry(id=_id, _session=self)
        entry.update_from_id()
        return entry

    # --- Tags ---

    def connect_tag_by_name(self, name: str) -> tag.Tag:
        _tag = tag.Tag(name, _session=self)
        _tag.update()
        return _tag

    def connect_tag_by_id(self, _id: int) -> tag.Tag:
        _tag = tag.Tag(id=_id, _session=self)
        _tag.update()
        return _tag

    # --- Calendar ---

    def connect_calendar(self, view_type: Literal["month", "day", "upcoming"] = "day",
                         _time: int | float | datetime = None, _course: int | str | course.Course = None):
        if isinstance(_time, datetime):
            _time = _time.timestamp()

        if isinstance(_course, course.Course):
            _course = _course.id

        resp = self.rq.get("https://vle.kegs.org.uk/calendar/view.php",
                           params={
                               "view": view_type,
                               "time": _time,
                               "course": _course
                           })
        ret = calendar.Calendar(_sess=self)

        soup = BeautifulSoup(resp.text, "html.parser")
        div = soup.find("div", {"class": "calendarwrapper"})

        if view_type == "month":
            ...
        elif view_type in ("day", "upcoming"):
            evlist = div.find("div", {"class": "eventlist"})
            for event_div in evlist.find_all("div", {"data-type": "event"}):
                cal_event = calendar.Event(_sess=self)

                head = event_div.find("div", {"class": "box card-header clearfix calendar_event_user"})

                cal_event.title = head.text.strip()

                body = event_div.find("div", {"class": "description card-body"})

                for row in body.find_all("div", {"class": "row"}):
                    row_type = row.find("i").get("title")

                    row_text = row.text.strip()
                    match row_type:
                        case "When":
                            cal_event.date = dateparser.parse(row_text)

                        case "Event type":
                            cal_event.type = row_text

                        case "Location":
                            cal_event.location = row_text

                        case "Description":
                            cal_event.description = row_text

                        case _:
                            warnings.warn(
                                f"Did not recognise calendar row type: {row_type!r} - report this on github: https://github.com/BigPotatoPizzaHey/kegscraper")
                ret.events.append(cal_event)

        return ret

    # -- Courses -- #
    def connect_recent_courses(self, limit: int = 10, offset: int = 0):
        data = self.webservice("core_course_get_recent_courses", limit=limit, offset=offset)
        return [course.Course.from_json(course_data) for course_data in data]

    def webservice(self, name, /, **args):
        """
        Directly interact with the webservice api
        :param name:methodname of webservice api, e.g. core_course_search_courses
        :param args:args to send to webservice api
        :return:
        """
        data: list = self.rq.post("https://vle.kegs.org.uk/lib/ajax/service.php",
                     params={"sesskey": self.sesskey},  # "info": name
                     json=[{"methodname": name, "args": args}]).json()

        skip = False
        if isinstance(data, dict):
            skip = "error" in data

        if not skip:
            data: dict[str, dict | str | int | float | None | bool | list] = data[0]

        if data["error"]:
            try:
                raise exceptions.WebServiceError(
                    f"{data['exception']['errorcode']!r}: {data['exception']['message']!r}")
            except KeyError:
                try:
                    raise exceptions.WebServiceError(
                        f"{data['errorcode']!r}: {data['error']!r}")
                except KeyError:
                    raise exceptions.WebServiceError(f"Error: {data}")

        return data["data"]

    def search_courses(self, query: str):
        data = self.webservice("core_course_search_courses", criterianame="tagid", criteriavalue=query)
        return data

    def connect_enrolled_courses(self, classification: Literal["future", "inprogress", "past"] = "inprogress",
                                 limit: int = 9999, offset: int = 0):
        data = self.webservice("core_course_get_enrolled_courses_by_timeline_classification",
                               classification=classification, limit=limit, offset=offset)
        return data


# --- * ---

def login(username: str, password: str) -> Session:
    """
    Login to kegsnet with a username and password
    :param username: Your username. Same as your email without '@kegs.org.uk'
    :param password: Your email password
    :return: a new session
    """

    session = requests.Session()
    session.headers = commons.headers.copy()

    response = session.get("https://vle.kegs.org.uk/login/index.php")

    soup = BeautifulSoup(response.text, "html.parser")
    login_token = soup.find("input", {"name": "logintoken"})["value"]

    session.post("https://vle.kegs.org.uk/login/index.php",
                 data={"logintoken": login_token,
                       "anchor": None,
                       "username": username,
                       "password": password
                       })

    return Session(rq=session)


def login_by_moodle(moodle_cookie: str) -> Session:
    """
    Login to kegsnet with just a moodle cookie (basically a session id)
    :param moodle_cookie: The MoodleSession cookie (see in the application/storage tab of your browser devtools when you log in)
    :return: A new session
    """
    session = requests.Session()
    session.cookies.set("MoodleSession", moodle_cookie)

    try:
        return Session(rq=session)
    except requests.exceptions.TooManyRedirects:
        raise ValueError(f"The moodle cookie {moodle_cookie!r} may be invalid/outdated.")
