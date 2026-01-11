from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field

from requests.structures import CaseInsensitiveDict

from . import session, digitalbook

@dataclass
class Course:
    id: int = None
    name: str = None
    subject: str = None
    smart: bool = field(repr=False, default=None)

    parent_id: int = field(repr=False, default=None)

    logo_url: str = field(repr=False, default=None)
    library_thumbnail_url: str = field(repr=False, default=None)
    course_name_image_url: str = field(repr=False, default=None)
    banner_background_image_url: str = field(repr=False, default=None)

    color: str = field(repr=False, default=None)
    banner_color: str = field(repr=False, default=None)
    lens_icon_color: str = field(repr=False, default=None)

    token_course: bool = field(repr=False, default=None)
    position: int = field(repr=False, default=None)
    self_study: Any = field(repr=False, default=None)
    no_contents_found_message: str = field(repr=False, default=None)
    curriculum: dict[str, str | dict[str, str | dict[str, str]]] = field(repr=False, default=None)

    _sess: session.Session = field(repr=False, default=None)

    def _get_img(self, url) -> tuple[bytes, CaseInsensitiveDict]:
        """
        Return img from url as a tuple: content, and headers
        """
        resp = self._sess.rq.get(f"https://www.kerboodle.com{url}")

        return resp.content, resp.headers

    @property
    def logo(self):
        return self._get_img(self.logo_url)

    @property
    def library_thumbnail(self):
        return self._get_img(self.library_thumbnail_url)
    @property
    def course_name_image(self):
        return self._get_img(self.course_name_image_url)
    @property
    def banner_background_image(self):
        return self._get_img(self.banner_background_image_url)

    @property
    def digital_books(self):
        data = self._sess.rq.get(f"https://www.kerboodle.com/api/courses/{self.id}/digital_books").json()

        return [digitalbook.DigitalBook.from_kwargs(_sess=self._sess, course=self, **attrs) for attrs in data]

    # --- * --- #
