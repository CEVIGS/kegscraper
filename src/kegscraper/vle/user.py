from __future__ import annotations

import dateparser
from bs4 import BeautifulSoup
from typing import Final
from dataclasses import dataclass, field
import warnings
from datetime import datetime

from . import session

DELETED_USER: Final[str] = "This user account has been deleted"
INVALID_USER: Final[str] = "Invalid user"
FORBIDDEN_USER: Final[str] = "The details of this user are not available to you"


@dataclass
class User:
    id: int = None

    name: str = None
    email: str = field(repr=False, default=None)
    image_url: str = field(repr=False, default=None)

    country: str = field(repr=False, default=None)
    city: str = field(repr=False, default=None)
    web_page: str = field(repr=False, default=None)

    interests: list = field(repr=False, default=None)
    courses: list = field(repr=False, default=None)

    first_access: datetime = field(repr=False, default=None)
    last_access: datetime = field(repr=False, default=None)

    description: str = field(repr=False, default=None)

    _session: session.Session = field(repr=False, default=None)

    flags: list[str] = field(repr=False, default_factory=list)

    @property
    def has_default_image(self) -> bool | None:
        if self.image_url is None:
            return None

        return self.image_url == "https://vle.kegs.org.uk/theme/image.php/trema/core/1585328846/u/f1"

    @property
    def profile_image(self) -> bytes:
        return self._session.rq.get(self.image_url).content

    def update_from_id(self):
        response = self._session.rq.get("https://vle.kegs.org.uk/user/profile.php",
                                        params={"id": self.id})
        text = response.text
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
            self.name = str(soup.find("div", {"class": "page-header-headings"}).contents[0].text)

            # Get user image
            self.image_url = soup.find_all("img", {"class": "userpicture"})[1].get("src")

            user_profile = soup.find("div", {"class": "userprofile"})
            self.description = user_profile.find("div", {"class": "description"})

            categories = user_profile.find_all("section", {"class", "node_category"})

            interests_node, interests, courses = None, [], []

            for category in categories:
                category_name = category.find("h3").contents[0]

                if category_name == "User details":
                    user_details = list(category.children)[1]

                    # This is an unordered list containing the Email, Country, City and Interest
                    content_nodes = user_details.find_all("li", {"class", "contentnode"})

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
                        courses.append((anchor.get("href").split('=')[-1],
                                        anchor.contents[0]))
                    if courses:
                        self.courses = courses

                elif category_name == "Miscellaneous":
                    ...

                elif category_name == "Reports":
                    ...

                elif category_name == "Login activity":
                    for i, activity in enumerate(category.find_all("dd")):
                        date_str = activity.contents[0]
                        date_str = date_str[:date_str.find('(')]

                        if i == 0:
                            self.first_access = dateparser.parse(date_str)
                        else:
                            self.last_access = dateparser.parse(date_str)
