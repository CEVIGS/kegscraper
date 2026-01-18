from __future__ import annotations

import json
import warnings
from typing_extensions import Any, Self, Optional
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import dateparser
from bs4 import BeautifulSoup

from . import session, course

from ..util import commons


@dataclass
@commons.with_kwargs
class DigitalBook:
    _sess: session.Session = field(repr=False)

    id: Optional[int] = None
    name: Optional[str] = None

    published: Optional[bool] = field(repr=False, default=None)
    is_new: Optional[bool] = field(repr=False, default=None)
    is_updated: Optional[bool] = field(repr=False, default=None)

    image_src: Optional[str] = field(repr=False, default=None)
    content_object_link: Optional[str] = field(repr=False, default=None)

    launcher: Optional[str] = field(repr=False, default=None)
    # image_class: str

    purchase_url: dict[str, str] = field(repr=False, default_factory=dict)
    available: dict[str, str] = field(repr=False, default_factory=dict)
    purchased: dict[str, str] = field(repr=False, default_factory=dict)
    subs_end_date: Optional[datetime] = field(repr=False, default=None)

    course: Optional[course.Course] = field(repr=False, default=None)

    # engine: str
    # purchase_link: str

    # offline_content_link: Any
    # offline_content_version: int

    # url: dict[str, str]

    # purchase_link_text: dict[str, str]
    # purchase_instruction_text: dict[str, str]
    # purchase_popup_title: dict[str, str]

    def __post_init__(self):
        if (
            not isinstance(self.subs_end_date, datetime)
            and self.subs_end_date is not None
        ):
            dt = dateparser.parse(str(self.subs_end_date))
            if dt is not None:
                self.subs_end_date = dt

    @classmethod
    def from_kwargs(cls, **kwargs) -> Self: ...

    @property
    def url(self):
        assert self.course is not None
        return f"https://www.kerboodle.com/api/courses/{self.course.id}/interactives/{self.id}.html"

    @property
    async def _interactive_html_data(self) -> dict | None:
        resp = await self._sess.rq.get(self.url)
        soup = BeautifulSoup(resp.text, "html.parser")

        data = None
        to_find = "\n//<![CDATA[\n        window.authorAPI.setup("
        for script in soup.find_all("script"):
            if script.contents:
                js = script.contents[0]
                i = js.find(to_find)
                if i >= 0:
                    data = commons.consume_json(js, i + len(to_find))
                    break

        assert isinstance(data, dict)
        return data

    @property
    async def _datajs_url(self) -> str:
        ihd = await self._interactive_html_data
        assert ihd is not None
        url = ihd["url"]
        parsed = urlparse(url)

        # remove index.html, add data.js instead

        path = "/".join(parsed.path.split("/")[:-1] + ["data.js"])

        return str(urlunparse(parsed._replace(path=path)))

    @property
    async def _datajs(self):
        resp = await self._sess.rq.get(await self._datajs_url)
        js = resp.text.strip()

        assert js.startswith("ajaxData = {")

        data: dict[str, str] = json.loads(js[len("ajaxData = ") : -1])

        ret = {}
        for key, val in data.items():
            try:
                ret[key] = BeautifulSoup(val, "xml")
            except Exception as e:
                warnings.warn(f"Caught exception: {e}")
                ret[key] = val

        return ret

    @property
    async def _catxml(self) -> BeautifulSoup:
        """
        :return: the other xml soup in datajs
        """
        xmldict = await self._datajs

        return xmldict[next(filter(lambda x: x != "LearningObjectInfo.xml", xmldict))]

    @property
    async def page_urls(self) -> list[str]:
        soup = await self._catxml

        ret: list[str] = []
        pages = soup.find("pages")
        assert pages is not None
        for page in pages.find_all("page"):
            url = page.get("url")
            if url.startswith("//"):
                url = f"https:{url}"

            ret.append(url)

        return ret
