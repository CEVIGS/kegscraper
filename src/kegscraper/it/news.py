"""
Get news page & load news category functions & related dataclasses
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup, Comment

from ..util import commons, exceptions


@dataclass
class Category:
    """
    A dataclass representing a category of a news item on kegsIT
    """
    id: int
    name: str


@dataclass
class NewsItem:
    """
    A news 'article'/post on the kegsIT website
    """
    id: int

    author: str = None
    title: str = None
    content: str = field(repr=False, default=None)

    date: datetime = None
    category: Category = None


def get_news_page(page: int = 1, category: int | Category = 7) -> NewsItem:
    """
    Get the news item at the specified page index
    :param category: Category of news
    :param page: Page index
    :return: The news item
    """
    if isinstance(category, Category):
        category = category.id

    # Find the page corresponding to the category & post
    response = commons.REQ.get(f"https://it.kegs.org.uk/",
                               params={
                                   "cat": category,
                                   "paged": page
                               })

    if response.status_code == 404:
        raise exceptions.NotFound(f"Could not find news page. Content: {response.content}")

    text = response.text
    soup = BeautifulSoup(text, "html.parser")

    anchor = soup.find("a", {"rel": "bookmark"})

    url = anchor.attrs.get("href")
    qparse = parse_qs(urlparse(url).query)

    news_id = int(qparse["p"][0])

    # Actually scrape the main page for this news item
    text = commons.REQ.get("https://it.kegs.org.uk/",
                           params={
                               "p": news_id
                           }).text
    soup = BeautifulSoup(text, "html.parser")

    title = soup.find("div", {"class": "singlepage"}).text

    date_elem = soup.find("abbr")
    date = datetime.fromisoformat(date_elem.attrs.get("title"))

    # There is a cheeky comment above the date element that we can try to webscrape
    comment = date_elem.parent.find(string=lambda _text: isinstance(_text, Comment)).extract()
    # It's actually in HTML format
    comment_text = BeautifulSoup(comment, "html.parser").text

    author = commons.webscrape_value(comment_text, "Written by ", " on")

    # Contents and category
    contents_div = soup.find("div", {"id": "content"})

    post_wrapper = contents_div.find("div", {"id": "singlepostwrapper"})
    category_anchor = post_wrapper.find("a", {"rel": "category"})

    # url = category_anchor.attrs.get("href")  # We already know the category index so we don't need to parse the link
    category_name = category_anchor.text
    category_obj = Category(category, category_name)

    # Get content
    content = contents_div.find("div", {"class": "entry"}).text.strip()

    return NewsItem(
        news_id,
        author,

        title,
        content,

        date,
        category_obj
    )


def load_news_category(category: int | Category = 7, *, limit: int = 10, offset: int = 0) -> list[NewsItem]:
    """
    Make mutliple requests to kegsIT to load an entire category of news data with a given offset and limit
    :param category: Category of news data to scrape. Defaults to the 'news' category
    :param limit: # of Posts to scrape
    :param offset: Starting post index
    :return: A list of posts aka news items
    """
    pages = []
    for page in commons.generate_page_range(limit, offset, 1, 1)[0]:
        # print(page)
        try:
            pages.append(get_news_page(page, category))

        except exceptions.NotFound:
            break

    return pages
