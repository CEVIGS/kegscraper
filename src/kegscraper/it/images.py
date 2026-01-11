from __future__ import annotations

from ..util import commons


def download_header(idx: int = 1):
    """
    Get a https://it.kegs.org.uk background header image (jpg) by idx
    :param idx: int 1-8 inclusive
    :return: (bytes) jpg image
    """
    if not 0 < idx < 9:
        return None
    return commons.REQ.get(f"https://it.kegs.org.uk/wp-content/themes/corporate-v3/headers/header_{idx}.jpg").content


def download_banner():
    return commons.REQ.get("https://it.kegs.org.uk/wp-content/themes/corporate-v3/images/banner-page.jpg").content
