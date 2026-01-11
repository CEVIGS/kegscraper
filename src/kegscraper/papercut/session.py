from __future__ import annotations

import mimetypes

import dateparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from dataclasses import dataclass

from ..util import commons

from . import org

@dataclass
class Session:
    username: str = None

    balance: float = None
    pages: int = None
    jobs: int = None

    trees: float = None
    co2: int = None  # Grams of co2
    energy: float = None  # joules
    since: datetime = None

    pages_graph: list[int] = None  # idx -1 is this week, -2 is last week, etc. (reverse?)

    organisation: org.Organisation = None

    rq: requests.Session = None

    def update_by_env(self):
        """
        Reassign session attributes (esp. self.organisation) by making a request to the environment dashboard
        """
        response = self.rq.get(f"http://printing.kegs.local:9191/environment/dashboard/{self.username}")

        self.update_by_env_dash_html(BeautifulSoup(response.text, "html.parser"))

    def logout(self):
        """
        Supposedly send a logout request. Probably doesn't do anything
        """
        self.rq.get("http://printing.kegs.local:9191/app?service=direct/1/UserSummary/$UserBorder.logoutLink")

    def update_from_dashboard(self):
        """
        Reassign session attributes by making a request to the main dashboard
        """
        resp = self.rq.get("http://printing.kegs.local:9191/app?service=page/UserSummary")
        self.update_by_dash_html(BeautifulSoup(resp.text, "html.parser"))

    def __post_init__(self):
        self.organisation = org.Organisation(sess=self)

    def update_by_env_dash_html(self, soup: BeautifulSoup):
        """
        Reassign session attributes (esp. self.organisation) by using the environment dashboard
        :param soup: Beautifulsoup representing the environment dashboard
        """
        # maybe scrape sheets (week/month), cost/month + trees/co2/energy

        # graph (canvas) - have to scrape js!
        for script in soup.find_all("script", {"type": "text/javascript"}):
            if script.contents:
                content = script.contents[0]
                find_str = "datasets : ["
                if find_str in content:
                    i = content.find(find_str)
                    content = content[i:]

                    find_str = "data : ["
                    f1 = content.find(find_str)
                    f2 = content[f1 + 8:].find(find_str) + f1 + 8

                    self.organisation.pages_graph = commons.consume_json(content, f1 + 6)  # num. pages
                    self.pages_graph = commons.consume_json(content, f2 + 6)  # num. pages

        for div in (soup.find("div", {"class": "box box50-100 medium"}),
                    soup.find("div", {"class": "box box50-100 darker"})):
            h2 = div.find("h2", {"class": "centered"})

            if h2.text.strip() == "Organization Impact":
                for stat in div.find_all("div", {"class": "env-stats-text"}) + \
                            div.find_all("div", {"class": "centered env-impact"}):
                    stat = stat.text.strip()

                    if stat.endswith(" trees"):
                        self.organisation.trees = float(stat.split()[0])
                    elif stat.endswith(" kg of CO2"):
                        self.organisation.co2 = 1000 * int(stat.replace(',', '').split()[0])
                    elif stat.endswith(" bulb hours"):
                        self.organisation.energy = 60 * 60 * 60 * int(stat.replace(',', '').split()[0])
                    elif stat.startswith("Since\n"):
                        self.organisation.since = dateparser.parse(stat[len("Since\n"):])

    def update_by_dash_html(self, soup: BeautifulSoup):
        """
        Reassign session attributes using the main dashboard html page
        :param soup: Beautifulsoup representing the html
        """
        self.username = soup.find("span", {"id": "username"}).text

        bal_div = soup.find("div", {"class": "widget stat-bal"})
        self.balance = float(bal_div.find("div", {"class": "val"}).text.strip()[1:])  # [1:] is to remove '£'

        pages_div = soup.find("div", {"class": "widget stat-pages"})
        self.pages = int(pages_div.find("div", {"class": "val"}).text)

        jobs_div = soup.find("div", {"class": "widget stat-jobs"})
        self.jobs = int(jobs_div.find("div", {"class": "val"}).text)

        env_div = soup.find("div", {"id": "enviro", "class": "col"})
        env_widget = env_div.find("div", {"class": "widget"})

        for li in env_widget.find_all("li"):
            key = li.get("class")[0]
            val = li.text.strip()

            match key:
                case "trees":
                    self.trees = float(val.split('%')[0]) / 100  # /100 because it's a percentage
                case "co2":
                    self.co2 = int(val.split('g')[0])
                case "energy":
                    val = float(val.split("hours")[0])  # hours running a 60W light bulb
                    val = val * 60 * 60  # seconds spent powering bulb
                    val *= 60  # 60W bulb
                    self.energy = val
                case "since-date":
                    val = val.replace("Since", '').strip()
                    self.since = dateparser.parse(val)

    def get_balance_graph(self, width: int=668, height: int=400) -> tuple[str, bytes]:
        resp = self.rq.get(f"http://printing.kegs.local:9191/app?service=chart/UserSummary/{width}/{height}/$Chart")
        # &sp=SBalance+history+for+{self.username}&69402papercut-mf")
        # it appears that the last part of the url is unnecessary

        return mimetypes.guess_extension(resp.headers["Content-Type"]), resp.content

def login(username: str, password: str) -> Session:
    """
    Login to papercut mf
    :param username:
    :param password:
    :return: A session object
    """
    sess = requests.Session()

    # Make an initial request (to set cookies)
    sess.get("http://printing.kegs.local:9191/user")

    # These headers were copied directly from my browser (no cookies)
    # Some of these headers have to be removed so that it works for other pages
    sess.headers = {
        # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        # "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        # "Content-Length": "302",
        # "Content-Type": "application/x-www-form-urlencoded",
        "Host": "printing.kegs.local:9191",
        # "Origin": "http://printing.kegs.local:9191",
        "Referer": "http://printing.kegs.local:9191/app",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    }

    resp = sess.post("http://printing.kegs.local:9191/app",
                     data={
                         "service": "direct/1/Home/$Form",
                         "sp": "S0",
                         "Form0": "$Hidden$0,$Hidden$1,inputUsername,inputPassword,$Submit$0,$PropertySelection",

                         "$Hidden$0": "true",
                         "$Hidden$1": "X",
                         "inputUsername": username,
                         "inputPassword": password,

                         "$Submit$0": "Log in",
                         "$PropertySelection": "en"
                     })

    ret = Session(rq=sess, username=username)
    # Since we receive the html of the main dashboard as the response content, we might as well parse it
    ret.update_by_dash_html(BeautifulSoup(resp.text, "html.parser"))

    return ret
