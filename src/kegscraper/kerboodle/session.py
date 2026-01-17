from __future__ import annotations

import warnings
import httpx

from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing_extensions import Optional

from . import course
from ..util import commons


@dataclass
class Session:
    rq: httpx.AsyncClient = field(repr=False)

    id: Optional[str] = None
    email: Optional[str] = None

    username: Optional[str] = field(repr=False, default=None)
    first_name: Optional[str] = field(repr=False, default=None)
    last_name: Optional[str] = field(repr=False, default=None)
    display_name: Optional[str] = field(repr=False, default=None)
    institution_code: Optional[str] = field(repr=False, default=None)
    account_type: Optional[str] = field(repr=False, default=None)

    async def connect_courses(self):
        data = (await self.rq.get("https://www.kerboodle.com/api/v2/courses")).json()

        ret: list[course.Course] = []
        data = data.get("data", [])
        for course_data in data:
            match course_data["type"]:
                case "course":
                    attrs = course_data["attributes"]
                    ret.append(course.Course(_sess=self, **attrs))

                case _:
                    warnings.warn(
                        f"Unknown course type: {course_data}. "
                        f"Please file an issue on github: https://github.com/BigPotatoPizzaHey/kegscraper/issues"
                    )

        return ret

    def connect_course_by_id(self, _id: int):
        return course.Course(id=_id, _sess=self)

    async def update_by_settings_api(self):
        # There is a huge amount of information in this response.
        # Only some of it is useful.
        data = (await self.rq.get("https://www.kerboodle.com/api/v2/settings")).json()[
            "data"
        ]

        attrs = data["attributes"]
        # possible useful attrs of attrs:
        # - client
        # - profile["school"]

        # --- #
        profile = attrs["profile"]

        self.id = profile["userid"]  # profile["id"] is something weird
        self.account_type = profile["type"]
        self.first_name = profile["first_name"]
        self.last_name = profile["last_name"]
        self.display_name = profile["display_name"]
        self.email = profile["email"]
        self.username = profile["username"]

        self.institution_code = profile["school"]["code"]

    async def logout(self):
        """Send a logout request to kerboodle. Might not have any effect"""
        resp = await self.rq.get("https://www.kerboodle.com/app")
        soup = BeautifulSoup(resp.text, "html.parser")

        csrf_token_tag = soup.find("meta", {"name": "csrf-token"})
        resp = await self.rq.post(
            "https://www.kerboodle.com/users/logout",
            data={
                "_method": "delete",
                "authenticity_token": (
                    csrf_token_tag.get("content") if csrf_token_tag is not None else "a"
                ),
            },
        )

        print(f"Logged out with status code {resp.status_code}")


async def login(
    institution_code: str, username: str, password: str, auto_update: bool = True
) -> Session:
    rq = httpx.AsyncClient()
    resp = await rq.get("https://www.kerboodle.com/users/login")
    soup = BeautifulSoup(resp.text, "html.parser")

    qs = commons.eval_inputs(soup)

    del qs["commit"]
    qs.update(
        {
            "user[login]": username,
            "user[password]": password,
            "user[institution_code]": institution_code,
        }
    )

    await rq.post("https://www.kerboodle.com/users/login", data=qs)
    sess = Session(rq=rq, institution_code=institution_code)

    if auto_update:
        await sess.update_by_settings_api()

    return sess
