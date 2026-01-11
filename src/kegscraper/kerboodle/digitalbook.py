from __future__ import annotations

import json
import warnings
from typing import Any, Self
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import dateparser
from bs4 import BeautifulSoup
import lxml

from . import session, course

from ..util import commons


@dataclass
@commons.with_kwargs
class DigitalBook:
    id: int = None
    name: str = None

    published: bool = field(repr=False, default=None)
    is_new: bool = field(repr=False, default=None)
    is_updated: bool = field(repr=False, default=None)

    image_src: str = field(repr=False, default=None)
    content_object_link: str = field(repr=False, default=None)

    launcher: str = field(repr=False, default=None)
    # image_class: str

    purchase_url: dict[str, str] = field(repr=False, default=None)
    available: dict[str, str] = field(repr=False, default=None)
    purchased: dict[str, str] = field(repr=False, default=None)
    subs_end_date: datetime = field(repr=False, default=None)

    course: course.Course = field(repr=False, default=None)
    _sess: session.Session = field(repr=False, default=None)

    # engine: str
    # purchase_link: str

    # offline_content_link: Any
    # offline_content_version: int

    # url: dict[str, str]

    # purchase_link_text: dict[str, str]
    # purchase_instruction_text: dict[str, str]
    # purchase_popup_title: dict[str, str]

    def __post_init__(self):
        if not isinstance(self.subs_end_date, datetime) and self.subs_end_date is not None:
            self.subs_end_date = dateparser.parse(str(self.subs_end_date))

    @classmethod
    def from_kwargs(cls, **kwargs) -> Self:
        ...

    @property
    def url(self):
        return f"https://www.kerboodle.com/api/courses/{self.course.id}/interactives/{self.id}.html"

    @property
    def _interactive_html_data(self) -> dict | None:
        resp = self._sess.rq.get(self.url)
        soup = BeautifulSoup(resp.text, "html.parser")

        data = None
        to_find = '\n//<![CDATA[\n        window.authorAPI.setup('
        for script in soup.find_all("script"):
            if script.contents:
                js = script.contents[0]
                i = js.find(to_find)
                if i >= 0:
                    data = commons.consume_json(js, i + len(to_find))
                    break

        return data

    @property
    def _datajs_url(self) -> str:
        url = self._interactive_html_data["url"]
        parsed = urlparse(url)

        # remove index.html, add data.js instead

        path = '/'.join(parsed.path.split('/')[:-1] + ["data.js"])

        return str(urlunparse(parsed._replace(path=path)))

    @property
    def _datajs(self):
        assert lxml # you need lxml to parse xml

        resp = self._sess.rq.get(self._datajs_url)
        js = resp.text.strip()

        assert js.startswith("ajaxData = {")

        data: dict[str, str] = json.loads(js[len("ajaxData = "):-1])

        ret = {}
        for key, val in data.items():
            try:
                ret[key] = BeautifulSoup(val, "xml")
            except Exception as e:
                warnings.warn(f"Caught exception: {e}")
                ret[key] = val

        return ret

    @property
    def _catxml(self) -> BeautifulSoup:
        """
        :return: the other xml soup in datajs
        """
        xmldict = self._datajs

        return xmldict[next(filter(lambda x: x != "LearningObjectInfo.xml", xmldict))]

    @property
    def page_urls(self) -> list[str]:
        soup = self._catxml

        ret = []
        pages = soup.find("pages")
        for page in pages.find_all("page"):
            url = page.get("url")
            if url.startswith("//"):
                url = f"https:{url}"

            ret.append(url)

        return ret
