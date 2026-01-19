from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import bs4
from typing_extensions import Any, Self, Optional

import dateparser
from bs4 import PageElement, BeautifulSoup

from . import session, user, tag, file
from ..util import commons, exceptions


@dataclass
class External:
    """Represents an external blog or an external blog entry"""

    _session: session.Session = field(repr=False)

    url: Optional[str] = None
    name: Optional[str] = None
    id: Optional[int] = None


@dataclass
class Comment:
    _session: session.Session = field(repr=False)

    id: Optional[int] = None
    content: Optional[BeautifulSoup] = field(repr=False, default=None)
    format: Optional[str] = "0"  # Idk what this is
    created: Optional[datetime] = None
    author: Optional[user.User] = None
    deletable: bool = False

    _entry: Optional[Entry] = field(repr=False, default=None)

    @classmethod
    def from_json(
        cls, data: dict[str, str | bool], _entry: Entry, _session: session.Session
    ) -> Self:
        return cls(
            data.get("id"),
            BeautifulSoup(data.get("content", ""), "html.parser"),
            data.get("format"),
            datetime.fromtimestamp(int(data.get("timecreated"))),
            _session.connect_partial_user(
                id=int(data.get("userid")), name=data.get("fullname")
            ),
            data.get("delete"),
            _entry,
            _session,
        )

    @property
    def text(self):
        return self.content.text

    def delete(self):
        response = self._session.rq.post(
            "https://vle.kegs.org.uk/comment/comment_ajax.php",
            data={
                "sesskey": self._session.sesskey,
                "action": "delete",
                "client_id": self._session.file_client_id,
                "itemid": self._entry.id,
                "area": "format_blog",
                "courseid": 1,
                "contextid": self._entry.context_id,
                "component": "blog",
                "commentid": self.id,
            },
        )
        if response:
            data = response.json()
            if data.get("error") == "Invalid comment ID":
                raise exceptions.NotFound("Invalud comment ID")
            else:
                return data
        else:
            extra = (
                f" This may be because you are not {self.author.name} ({self.author.id})"
                if self._session.user_id != self.author.id
                else ""
            )
            warnings.warn(f"Possibly couldn't delete {self}.{extra}")


@dataclass
class Entry:
    _session: session.Session = field(repr=False)

    id: Optional[int] = None
    subject: Optional[str] = None
    author: Optional[user.User] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    publishstate: Optional[str] = None
    content: PageElement | Any | None = field(repr=False, default=None)

    attachments: list[file.File] | None = None
    images: PageElement | Any = field(repr=False, default=None)
    tags: list[tag.Tag] | None = None

    external_blog: Optional[External] = None
    external_blog_entry: Optional[External] = None

    context_id: Optional[int] = None

    @property
    def url(self):
        return f"https://vle.kegs.org.uk/blog/index.php?entryid={self.id}"

    @classmethod
    def from_json(cls, data: dict[str, Any], _sess: session.Session) -> Self:
        if data["module"] == "blog_external":
            ext_be = External(url=data["uniquehash"], _session=_sess)
            ext = External(id=data["moduleid"], _session=_sess)
        else:
            ext_be = None
            ext = None

        return cls(
            _session=_sess,
            id=data["id"],
            subject=data["subject"],
            author=user.User(id=data["userid"], _session=_sess),
            date_created=datetime.fromtimestamp(data["created"]),
            date_modified=datetime.fromtimestamp(data["lastmodified"]),
            publishstate=data["publishstate"],
            content=BeautifulSoup(data["summary"], "html.parser"),
            attachments=[
                file.File.from_json2(attch, _sess) for attch in data["attachmentfiles"]
            ],
            tags=[tag.Tag.from_json(td, _sess) for td in data["tags"]],
            external_blog=ext,
            external_blog_entry=ext_be,
        )

    async def update_from_id(self):
        resp = await self._session.rq.get(
            "https://vle.kegs.org.uk/blog/index.php", params={"entryid": self.id}
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        div = soup.find("div", {"id": f"b{self.id}"})
        if div is None:
            raise exceptions.NotFound(
                f"BlogEntry #{self.id}, ({self}) does not seem to exist. It may have been deleted, or may never have existed, or you may be logged out."
            )

        self.update_from_div(div)

    def update_from_div(self, div: bs4.Tag):
        header = div.find("div", {"class": "row header clearfix"})
        main = div.find("div", {"class": "row maincontent clearfix"})

        if header is None and main is None:
            raise exceptions.NotFound(
                f"BlogEntry #{self.id}, ({self}) does not seem to exist. It may have been deleted, or may never have existed, or you may be logged out."
            )

        self.id = int(div["id"][1:])

        assert header is not None
        self.subject = header.find("div", {"class": "subject"}).text

        author_anchor = header.find("div", {"class": "author"}).find("a")
        parse = urlparse(author_anchor["href"])
        qparse = parse_qs(parse.query)

        author_id = int(qparse["id"][0])

        self.author = self._session.connect_partial_user(
            id=author_id, name=author_anchor.text
        )

        date_str = author_anchor.next.next.text
        self.date_created = dateparser.parse(date_str)

        external_div = header.find("div", {"class": "externalblog"})
        if external_div:
            external_anchor = external_div.find("a")
            if external_anchor:
                self.external_blog = External(
                    url=external_anchor["href"],
                    name=external_anchor.text,
                    _session=self._session,
                )

        # Get actual blog content
        assert main is not None
        div = main.find("div", {"class": "audience"})
        audience = div.text.strip()
        self.publishstate = {"Anyone on this site": "site"}.get(audience)

        self.images = main.find("div", {"class": "attachedimages"})

        self.content = main.find("div", {"class": "no-overflow"}).find(
            "div", {"class": "no-overflow"}
        )

        external_div = main.find("div", {"class": "externalblog"})
        if external_div:
            external_anchor = external_div.find("a")
            if external_anchor:
                self.external_blog_entry = External(
                    url=external_anchor["href"],
                    name=external_anchor.text,
                    _session=self._session,
                )

        tag_list = main.find("div", {"class": "tag_list"})
        if tag_list:
            tag_list = tag_list.find_all("li")

        self.tags = []
        if tag_list:
            for tag_data in tag_list:
                tag_a = tag_data.find("a")

                # We could probably also get the anchor text, but this is more robust
                parse = urlparse(tag_a["href"])
                qparse = parse_qs(parse.query)

                self.tags.append(tag.Tag(name=qparse["tag"][0], _session=self._session))

        mdl = main.find("div", {"class": "mdl-left"})
        njs_url = mdl.find("a", {"class": "showcommentsnonjs"})["href"]
        parse = urlparse(njs_url)
        qparse = parse_qs(parse.query)
        self.context_id = int(qparse["comment_context"][0])

    async def get_comments(self, *, limit: int = 1, offset: int = 0) -> list[Comment]:
        if self.context_id is None:
            await self.update_from_id()

        data_lst = []
        for page, _ in zip(
            *commons.generate_page_range(
                limit, offset, items_per_page=999, starting_page=0
            )
        ):
            data_lst += (
                await self._session.rq.post(
                    "https://vle.kegs.org.uk/comment/comment_ajax.php",
                    data={
                        "sesskey": await self._session.sesskey,
                        "action": "get",
                        "client_id": await self._session.file_client_id,
                        "itemid": self.id,
                        "area": "format_blog",
                        "courseid": "1",
                        "contextid": self.context_id,
                        "component": "blog",
                        "page": page,
                    },
                )
            ).json()["list"]

        return [Comment.from_json(data, self, self._session) for data in data_lst]

    async def post_comment(self, content: str) -> Comment:
        if self.context_id is None:
            await self.update_from_id()

        resp = await self._session.rq.post(
            "https://vle.kegs.org.uk/comment/comment_ajax.php",
            data={
                "sesskey": await self._session.sesskey,
                "action": "add",
                "client_id": await self._session.file_client_id,
                "itemid": self.id,
                "area": "format_blog",
                "courseid": 1,
                "contextid": self.context_id,
                "component": "blog",
                "content": content,
            },
        )

        ret = Comment.from_json(resp.json(), self, self._session)
        return ret
