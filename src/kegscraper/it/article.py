from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, PageElement

from ..util import commons, exceptions

@dataclass
class Article:
    id: int
    title: str = None
    contents: PageElement = field(repr=False, default=None)

    @property
    def text(self):
        return self.contents.text.strip()

    def update_by_id(self):
        response = commons.REQ.get("https://it.kegs.org.uk/", params={
            "page_id": self.id
        })

        if not "page_id" in parse_qs(urlparse(response.url).query):
            raise exceptions.NotFound(f"'article' id={self.id} is not an article. (redirected to {response.url})")

        soup = BeautifulSoup(response.text, "html.parser")
        post = soup.find("div", {"id": "content"})

        try:
            heading = post.find("div", {"class": "singlepage"})

            self.title = heading.text
            self.contents = post
            # ^^ the reason why the whole post is used rather than only the 'entry' div is because of article #22,
            # which doesn't contain an entry div: https://it.kegs.org.uk/?page_id=22

        except AttributeError as e:
            raise exceptions.NotFound(f"article id={self.id} probably doesn't exist. error: {e}")


def get_article_by_id(_id: int):
    article = Article(_id)
    article.update_by_id()
    return article
