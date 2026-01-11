import requests
from bs4 import BeautifulSoup

from ..util import commons

def api_fetch(url: str, rq: requests.Session = None):
    """Make an api call to the oliver library api."""

    if rq is None:
        rq = commons.REQ

    url = f"https://kegs.oliverasp.co.uk/library/home/api/{url}"
    # For some reason it seems that it provides us with some query params then redirects us
    text = commons.REQ.get(url).text
    soup = BeautifulSoup(text, "html.parser")

    qs = {}

    # Parse inputs
    inputs = soup.find_all("input")
    for _input in inputs:
        attrs = _input.attrs
        qs[attrs.get("name")] = attrs.get("value")

    # Parse select elements
    selects = soup.find_all("select")
    for select in selects:
        attrs = select.attrs
        options = select.find_all("option")

        # If there's no predefined value just pick the first
        selected_id = attrs.get("selected")
        selected = None
        for option in options:
            if not selected:
                if selected_id is not None:
                    if option.text == selected_id:
                        selected = option
                else:
                    selected = option

        qs[attrs.get("name")] = selected.attrs.get("value")

    return rq.get(url, params=qs).json()
