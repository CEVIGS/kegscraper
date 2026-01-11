from __future__ import annotations

import atexit
import warnings
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from . import course

from ..util import commons


@dataclass
class Session:
    id: str = None
    email: str = None

    username: str = field(repr=False, default=None)
    first_name: str = field(repr=False, default=None)
    last_name: str = field(repr=False, default=None)
    display_name: str = field(repr=False, default=None)
    institution_code: str = field(repr=False, default=None)
    account_type: str = field(repr=False, default=None)

    rq: requests.Session | None = field(repr=False, default=None)

    def __post_init__(self):
        atexit.register(self.logout)

    def connect_courses(self):
        data = self.rq.get("https://www.kerboodle.com/api/v2/courses").json()

        ret = []
        data = data.get("data", [])
        for course_data in data:
            match course_data["type"]:
                case "course":
                    attrs = course_data["attributes"]
                    ret.append(course.Course(_sess=self, **attrs))

                case _:
                    warnings.warn(f"Unknown course type: {course_data}. "
                                  f"Please file an issue on github: https://github.com/BigPotatoPizzaHey/kegscraper/issues")

        return ret

    def connect_course_by_id(self, _id: int):
        return course.Course(id=_id, _sess=self)

    def update_by_settings_api(self):
        # There is a huge amount of information in this response.
        # Only some of it is useful.
        data = self.rq.get("https://www.kerboodle.com/api/v2/settings").json()["data"]

        attrs = data["attributes"]
        # possible useful attrs of attrs:
        # - client
        # - profile["school"]

        # --- #
        profile = attrs["profile"]

        self.id = profile["userid"] # profile["id"] is something weird
        self.account_type = profile["type"]
        self.first_name = profile["first_name"]
        self.last_name = profile["last_name"]
        self.display_name = profile["display_name"]
        self.email = profile["email"]
        self.username = profile["username"]

        self.institution_code = profile["school"]["code"]

    def logout(self):
        """Send a logout request to kerboodle. Might not have any effect"""
        resp = self.rq.get("https://www.kerboodle.com/app")
        soup = BeautifulSoup(resp.text, "html.parser")

        resp = self.rq.post("https://www.kerboodle.com/users/logout", data={
            "_method": "delete",
            "authenticity_token": soup.find("meta", {"name": "csrf-token"}).get("content")
        })

        print(f"Logged out with status code {resp.status_code}")

        self.rq = None

def login(institution_code: str, username: str, password: str, auto_update: bool = True) -> Session:
    rq = requests.Session()
    resp = rq.get("https://www.kerboodle.com/users/login")
    soup = BeautifulSoup(resp.text, "html.parser")

    qs = commons.eval_inputs(soup)

    del qs["commit"]
    qs.update({
        "user[login]": username,
        "user[password]": password,
        "user[institution_code]": institution_code
    })

    rq.post("https://www.kerboodle.com/users/login", data=qs)
    sess = Session(rq=rq, institution_code=institution_code)

    if auto_update:
        sess.update_by_settings_api()

    return sess
