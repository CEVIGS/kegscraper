"""Post, Discussion and Forum classes"""
from __future__ import annotations

from urllib.parse import urlparse, parse_qs
from datetime import datetime

import dateparser
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, NavigableString, PageElement

from . import session, user


@dataclass
class Post:
    """Represents a post in a discussion in a forum on the kegsnet website"""

    id: int = None
    """Actually the integer in the url fragment that links to this post, which is attached to the discussion link"""
    creator: user.User = None
    date: datetime = None
    title: str = None
    content: str = field(repr=False, default=None)

    _discussion: Discussion = None
    _session: session.Session = field(repr=False, default=None)

    def update_from_html(self, elem: PageElement):
        # --- Data from the <header> tag
        header = elem.find("header")
        hdata = header.find("div", {"class": "flex-column"})

        self.title = hdata.find("h3").text

        user_anchor = hdata.find("a")
        user_url = user_anchor.attrs.get("href")
        uid = int(
            parse_qs(
                urlparse(user_url).query
            ).get("id")[0]
        )

        self.creator = self._session.connect_user_by_id(uid)
        # We can actually provide the name of the creator, even if other data is inaccessible
        self.creator.name = user_anchor.text

        self.date = dateparser.parse(
            header.find("time").text
        )

        # Other data
        permalink = elem.find("a", {"title": "Permanent link to this post"}).attrs.get("href")
        parse = urlparse(permalink)
        self.id = int(parse.fragment[1:])

        self.content = str(elem.find("div", {"class": "post-content-container"}))


@dataclass
class Discussion:
    """Represents a discussion within a forum on the kegsnet website"""
    id: int = None

    name: str = None
    # author: user.User = None # It only shows a name & pfp - but not an actual link

    date_created: datetime = None
    # last_post: Post = None
    reply_count: int = None

    _forum: Forum = field(repr=False, default=None)
    _session: session.Session = field(repr=False, default=None)
    _top_post: Post = field(repr=False, default=None)

    posts: list[Post] = field(repr=False, default_factory=lambda: [])

    def update_from_forum_html(self, elem: PageElement) -> None:
        """
        Update the discussion from HTML on a forum's page
        :param elem: the HTML data as a bs4.PageElement object
        """
        for i, item in enumerate(elem.find_all("td")):
            if i == 0:
                # Star this discussion
                ...

            elif i == 1:
                # Name
                anchor = item.find("a")
                self.name = anchor.text

                # You can also get id from the url
                parse = urlparse(anchor.attrs.get("href"))
                qparse = parse_qs(parse.query)
                self.id = int(qparse.get("d")[0])

            elif i == 2:
                # Started by
                ...

            elif i == 3:
                # Reply count
                self.reply_count = int(item.find("a").text.strip())

            elif i == 4:
                # Last post
                ...

            elif i == 5:
                # Date created
                text = item.text.strip()
                self.date_created = dateparser.parse(text)

            else:
                break

    def update(self):
        """
        Update the discussion from the corresponding url. Requires an id
        :return:
        """
        response = self._session.rq.get("https://vle.kegs.org.uk/mod/forum/discuss.php",
                                        params={
                                    "d": self.id,
                                    "mode": 1
                                })

        soup = BeautifulSoup(response.text, "html.parser")

        self.name = soup.find("h3", {"class": "discussionname"}).text
        core_attrs = {"data-region-content": "forum-post-core"}

        post_htmls = soup.find_all("div", core_attrs)
        top_post_html = soup.find("div", {"class": "firstpost"}).find("div", core_attrs)

        self._top_post = Post(_discussion=self, _session=self._session)
        self._top_post.update_from_html(top_post_html)

        self.posts = []
        for post_html in post_htmls:
            self.posts.append(Post(_discussion=self, _session=self._session))
            self.posts[-1].update_from_html(post_html)

    @property
    def url(self) -> str:
        """Get the url of this discussion"""
        return f"https://vle.kegs.org.uk/mod/forum/discuss.php?d={self.id}"

    @property
    def top_post(self) -> Post:
        """
        Fetch the first post in a discussion
        """
        if not self._top_post:
            self.update()

        return self._top_post


@dataclass
class Forum:
    """Represents a forum on KEGSNET - e.g. the news forum"""
    id: int

    name: str = None
    description: str = None
    contents: list[Discussion] = None

    _session: session.Session = field(repr=False, default=None)

    def update_by_id(self):
        """Update attributes by requesting the corresponding webpage. Requires an id"""
        response = self._session.rq.get("https://vle.kegs.org.uk/mod/forum/view.php",
                                        params={"f": self.id})
        soup = BeautifulSoup(response.text, "html.parser")

        container = soup.find("div", {"role": "main"})
        for i, element in enumerate(container.children):
            if element.name == "h2":
                self.name = element.text

            elif element.name == "div":
                div_id = element.attrs.get("id")

                if div_id == "intro":
                    self.description = element.text

                else:
                    element: PageElement
                    post_list = element.find("table", {"class": "table table-hover table-striped discussion-list"})

                    for tpart in post_list.children:
                        tpart: PageElement
                        if tpart.name == "tbody":
                            discussions = []

                            # List of discussions
                            for discuss_elem in tpart.children:
                                if not isinstance(discuss_elem, NavigableString):
                                    discussion = Discussion(_forum=self, _session=self._session)
                                    discussion.update_from_forum_html(discuss_elem)
                                    discussions.append(discussion)

                            self.contents = discussions
