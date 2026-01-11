"""
Class representing tags accessible through here: https://vle.kegs.org.uk/tag/index.php?tag=woodlouse
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs
from typing import Self

import dateparser
import requests
from bs4 import BeautifulSoup, PageElement
from . import session, user, blog
from ..util import commons


@dataclass
class Tag:
    name: str = None
    exists: bool = None

    description: PageElement = field(default=None, repr=False)
    related_tags: list[Tag] = field(default_factory=list)

    id: int = None
    flagged_inappropriate: bool = field(repr=False, default=False)

    item_id: str = None

    _session: session.Session = field(repr=False, default=None)

    @classmethod
    def from_json(cls, data: dict, _sess: session.Session) -> Self:
        return cls(
            flagged_inappropriate=bool(data["flag"]),
            id=data["id"],
            item_id=data["itemid"],
            name=data["name"], # == rawname?
            exists=True,
            # instance id, context id?
            _session=_sess
        )

    @property
    def url(self):
        if self.id:
            return f"https://vle.kegs.org.uk/tag/index.php?id={self.id}"
        elif self.name:
            return f"https://vle.kegs.org.uk/tag/index.php?tag={self.name}"
        else:
            warnings.warn(f"Could not infer a Tag id for {self}")
            return ""

    def _update_from_response(self, response: requests.Response):
        self.exists = response.url != "https://vle.kegs.org.uk/tag/search.php"
        if self.exists:
            soup = BeautifulSoup(response.text, "html.parser")
            main = soup.find("div", {"role": "main"})

            self.name = main.find("h2").text

            mng_box = main.find("div", {"class": "tag-management-box"})
            tedit = mng_box.find("a", {"class": "edittag"})
            href = tedit.attrs.get("href", '')
            q_parse = parse_qs(urlparse(href).query)
            self.id = int(q_parse.get("id")[0])

            # get desc
            self.description = main.find("div", {"class": "tag-description"})

            # get related tags
            self.related_tags.clear()
            related_tag_div = main.find("div", {"class": "tag-relatedtags"})
            if related_tag_div:
                for li in related_tag_div.find_all("li"):
                    href = li.find("a").attrs["href"]
                    if href == '#':
                        continue

                    parsed = urlparse(href)
                    q_parse = parse_qs(parsed.query)
                    related_tag_name = q_parse["tag"][0]
                    self.related_tags.append(
                        Tag(
                            related_tag_name,
                            _session=self._session
                        )
                    )

    def update(self):
        """
        Update by name or id
        """
        response = self._session.rq.get(self.url)
        self._update_from_response(response)

    def connect_interested_users(self, limit: int = 5, offset: int = 0):
        users = []

        for page in commons.generate_page_range(limit, offset, 5, 0)[0]:
            data = self._session.webservice("core_tag_get_tagindex", tagindex={
                "tc": 1,
                "tag": self.name,
                "ta": 1,  # 1 = users, 3 = courses, 7 = blog posts.
                "page": str(page)
            })

            soup = BeautifulSoup(data["content"], "html.parser")

            lis = soup.find_all("li", {"class": "media"})
            if not lis:
                break # if it is empty, don't need to make more webreqs

            for li in lis:
                a = li.find("a")
                href = a.attrs["href"]
                q_parse = parse_qs(urlparse(href).query)

                uid = int(q_parse["id"][0])

                img = a.find("img")
                src = img.attrs["src"]

                body = li.find("div", {"class": "media-body"})
                name = body.text.strip()

                users.append(user.User(id=uid, name=name, image_url=src, _session=self._session))

        return users

    def connect_tagged_blog_entries(self, limit: int = 5, offset: int = 0):
        entries = []

        for page in commons.generate_page_range(limit, offset, 5, 0)[0]:
            data = self._req_get_tagindex(page, 7).json()[0]["data"]["content"]
            soup = BeautifulSoup(data, "html.parser")

            for li in soup.find_all("li", {"class": "media"}):
                a = li.find("a")
                href = a.attrs["href"]
                q_parse = parse_qs(urlparse(href).query)

                uid = int(q_parse["id"][0])

                img = a.find("img")
                src = img.attrs["src"]

                body = li.find("div", {"class": "media-body"})

                entry_a = body.find("a")
                subject = entry_a.contents[0].strip()

                href = entry_a.attrs["href"]
                q_parse = parse_qs(urlparse(href).query)
                entry_id = int(q_parse["entryid"][0])

                muted = body.find("div", {"class": "muted"})
                split = muted.text.split(',')
                author_name = split[0].strip()
                date = dateparser.parse(','.join(split[1:]))

                author = user.User(id=uid, name=author_name, image_url=src)

                entries.append(
                    blog.Entry(
                        id=entry_id,
                        subject=subject,
                        date_created=date,
                        author=author,
                        _session=self._session
                    )
                )

        return entries

    def edit(self, new_description: str | PageElement = None, related_tags: list[Tag | str] = None):
        if new_description is None:
            new_description = self.description
        if related_tags is None:
            related_tags = self.related_tags

        if not isinstance(new_description, str):
            if new_description is not None:
                new_description = new_description.prettify()
            # else:
            #     new_description = ''

        related_tags = list(map(lambda x: x if isinstance(x, str) else x.name, related_tags))

        response = self._session.rq.get("https://vle.kegs.org.uk/tag/edit.php", params={"id": self.id})

        soup = BeautifulSoup(response.text, "html.parser")

        # it appears that order matters??? Not sure
        data = [
                   ("id", self.id),
                   ("returnurl", ''),
                   ("sesskey", self._session.sesskey),
                   ("_qf__tag_edit_form", 1),
                   ("mform_isexpanded_id_tag", new_description),
                   ("description_editor[text]", ''),
                   ("description_editor[format]", 1),
                   ("description_editor[itemid]", soup.find("input", {"name": "description_editor[itemid]"})),
                   ("relatedtags", "_qf__force_multiselect_submission"),
               ] + [("relatedtags[]", tagname) for tagname in related_tags] + [
                   ("submitbutton", "Update"),
               ]

        return self._session.rq.post("https://vle.kegs.org.uk/tag/edit.php",
                                     data=data)
