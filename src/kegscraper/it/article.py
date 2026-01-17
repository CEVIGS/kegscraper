from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup

import bs4

from ..util import commons, exceptions


@dataclass
class Article:
    id: int
    title: str | None = None
    contents: bs4.PageElement | bs4.Tag | None = field(repr=False, default=None)

    @property
    def text(self):
        if self.contents is None:
            return ""
        return self.contents.text.strip()

    async def update_by_id(self):
        resp = await commons.REQ.get(
            "https://it.kegs.org.uk/", params={"page_id": self.id}
        )

        if not "page_id" in parse_qs(resp.url.query.decode()):
            raise exceptions.NotFound(
                f"'article' id={self.id} is not an article. (redirected to {resp.url})"
            )

        soup = BeautifulSoup(resp.text, "html.parser")
        post = soup.find("div", {"id": "content"})

        if post is None:
            raise exceptions.NotFound(f"article {self.id=} probably doesn't exist.")
        heading = post.find("div", {"class": "singlepage"})
        if heading is None:
            raise exceptions.NotFound(f"article {self.id=} is bad")

        self.title = heading.text
        self.contents = post
        # ^^ the reason why the whole post is used rather than only the 'entry' div is because of article #22,
        # which doesn't contain an entry div: https://it.kegs.org.uk/?page_id=22


async def get_article_by_id(_id: int) -> Article | None:
    try:
        article = Article(_id)
        await article.update_by_id()
    except exceptions.NotFound:
        return None
    return article
