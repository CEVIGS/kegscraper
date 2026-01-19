from __future__ import annotations

import dateparser
from bs4 import BeautifulSoup
from typing_extensions import Final, Optional
from dataclasses import dataclass, field
import warnings
from datetime import datetime

from . import session

DELETED_USER: Final[str] = "This user account has been deleted"
INVALID_USER: Final[str] = "Invalid user"
FORBIDDEN_USER: Final[str] = "The details of this user are not available to you"


@dataclass
class User:
    _session: session.Session = field(repr=False)

    id: Optional[int] = None

    name: Optional[str] = None
    email: Optional[str] = field(repr=False, default=None)
    image_url: Optional[str] = field(repr=False, default=None)

    country: Optional[str] = field(repr=False, default=None)
    city: Optional[str] = field(repr=False, default=None)
    web_page: Optional[str] = field(repr=False, default=None)

    interests: Optional[list] = field(repr=False, default=None)
    courses: Optional[list] = field(repr=False, default=None)

    first_access: Optional[datetime] = field(repr=False, default=None)
    last_access: Optional[datetime] = field(repr=False, default=None)

    description: Optional[str] = field(repr=False, default=None)

    flags: list[str] = field(repr=False, default_factory=list)

    @property
    def has_default_image(self) -> bool | None:
        if self.image_url is None:
            return None

        return (
            self.image_url
            == "https://vle.kegs.org.uk/theme/image.php/trema/core/1585328846/u/f1"
        )

    @property
    async def profile_image(self) -> bytes:
        assert self.image_url is not None, "Need image url to get image!"
        return (await self._session.rq.get(self.image_url)).content

    async def update_from_id(self):
        resp = await self._session.rq.get(
            "https://vle.kegs.org.uk/user/profile.php", params={"id": self.id}
        )
        text = resp.text
        soup = BeautifulSoup(text, "html.parser")

        self.flags = []

        if DELETED_USER in text:
            self.flags.append(DELETED_USER)
            warnings.warn(f"User id {self.id} is deleted!")

        elif INVALID_USER in text:
            self.flags.append(INVALID_USER)
            warnings.warn(f"User id {self.id} is invalid!")

        elif FORBIDDEN_USER in text:
            self.flags.append(FORBIDDEN_USER)
            warnings.warn(f"User id {self.id} is forbidden!")

        else:
            # Get user's name
            elem = soup.find("div", {"class": "page-header-headings"})
            assert elem is not None
            self.name = str(elem.contents[0].text)

            # Get user image
            self.image_url = soup.find_all("img", {"class": "userpicture"})[1].get(
                "src"
            )

            user_profile = soup.find("div", {"class": "userprofile"})
            assert user_profile is not None
            self.description = user_profile.find("div", {"class": "description"})

            categories = user_profile.find_all("section", {"class", "node_category"})

            interests_node, interests, courses = None, [], []

            for category in categories:
                category_name = category.find("h3").contents[0]

                if category_name == "User details":
                    user_details = list(category.children)[1]

                    # This is an unordered list containing the Email, Country, City and Interest
                    content_nodes = user_details.find_all(
                        "li", {"class", "contentnode"}
                    )

                    for li in content_nodes:
                        dl = li.find("dl")

                        dd = dl.find("dd")
                        item_name = dl.find("dt").contents[0]

                        if item_name == "Email address":
                            self.email = dl.find("a").contents[0]

                        elif item_name == "City/town":
                            self.city = dd.contents[0]

                        elif item_name == "Country":
                            self.country = dd.contents[0]

                        elif item_name == "Web page":
                            self.web_page = dl.find("a").get("href")

                        elif item_name == "Interests":
                            interests_node = dl

                    if interests_node is not None:
                        try:
                            for anchor in interests_node.find_all("a"):
                                interests.append(anchor.contents[0][21:])
                        except IndexError:
                            ...

                        if interests:
                            self.interests = interests

                elif category_name == "Course details":
                    for anchor in category.find_all("a"):
                        courses.append(
                            (anchor.get("href").split("=")[-1], anchor.contents[0])
                        )
                    if courses:
                        self.courses = courses

                elif category_name == "Miscellaneous":
                    ...

                elif category_name == "Reports":
                    ...

                elif category_name == "Login activity":
                    for i, activity in enumerate(category.find_all("dd")):
                        date_str = activity.contents[0]
                        date_str = date_str[: date_str.find("(")]

                        if i == 0:
                            self.first_access = dateparser.parse(date_str)
                        else:
                            self.last_access = dateparser.parse(date_str)
