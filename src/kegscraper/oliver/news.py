from . import utils


def get_news() -> dict:
    """
    Fetch news from the api as JSON. Will be parsed later
    """
    data = utils.api_fetch("news")
    # Parse this...
    return data
