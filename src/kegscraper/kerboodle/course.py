from __future__ import annotations

from typing_extensions import Any, Optional
from dataclasses import dataclass, field

from requests.structures import CaseInsensitiveDict

from . import session, digitalbook
from kegscraper.util import commons


@dataclass
class Course:
    _sess: session.Session = field(repr=False)

    id: Optional[int] = None
    name: Optional[str] = None
    subject: Optional[str] = None
    smart: Optional[bool] = field(repr=False, default=None)

    parent_id: Optional[int] = field(repr=False, default=None)

    logo_url: Optional[str] = field(repr=False, default=None)
    library_thumbnail_url: Optional[str] = field(repr=False, default=None)
    course_name_image_url: Optional[str] = field(repr=False, default=None)
    banner_background_image_url: Optional[str] = field(repr=False, default=None)

    color: Optional[str] = field(repr=False, default=None)
    banner_color: Optional[str] = field(repr=False, default=None)
    lens_icon_color: Optional[str] = field(repr=False, default=None)

    token_course: Optional[bool] = field(repr=False, default=None)
    position: Optional[int] = field(repr=False, default=None)
    self_study: Any = field(repr=False, default=None)  # idk what this is?
    no_contents_found_message: Optional[str] = field(repr=False, default=None)
    curriculum: dict[str, str | dict[str, str | dict[str, str]]] = field(
        repr=False, default_factory=dict
    )

    async def _get_img(self, url) -> tuple[bytes, str | None]:
        """
        Return img from url as a tuple: content, and fileext
        """
        resp = await self._sess.rq.get(f"https://www.kerboodle.com{url}")

        # return commons.resp_to_file(resp)
        return (
            resp.content,
            None,
        )  # not sure why, but it seems like the content disposition isnt valid or smth. issue on gh (35)

    @property
    async def logo(self):
        return await self._get_img(self.logo_url)

    @property
    async def library_thumbnail(self):
        return await self._get_img(self.library_thumbnail_url)

    @property
    async def course_name_image(self):
        return await self._get_img(self.course_name_image_url)

    @property
    async def banner_background_image(self):
        return await self._get_img(self.banner_background_image_url)

    @property
    async def digital_books(self):
        data = (
            await self._sess.rq.get(
                f"https://www.kerboodle.com/api/courses/{self.id}/digital_books"
            )
        ).json()

        return [
            digitalbook.DigitalBook.from_kwargs(_sess=self._sess, course=self, **attrs)
            for attrs in data
        ]

    # --- * --- #
