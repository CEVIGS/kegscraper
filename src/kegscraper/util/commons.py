"""
Utility functions/variables used commonly across the module
"""

import json
import string
import warnings
import copy
from datetime import datetime
from typing import Any, Final
from inspect import signature

import requests
from bs4 import BeautifulSoup

from . import exceptions

REQ: Final[requests.Session] = requests.Session()

DIGITS: Final = tuple("0123456789")

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
    "referer": "https://kegs.org.uk/",
}


def webscrape_value(raw, text_before, text_after, cls: type = str, i1: int = 1, i2: int = 0) -> str | Any:
    return cls(
        raw.split(text_before)[i1] \
            .split(text_after)[i2]
    )


def webscrape_section(raw: str, before: str | int = '', after: str | int = '', cls: type = str) -> str | Any:
    def _toint(val: str | int) -> int:
        return val if isinstance(val, int) else len(val)

    before, after = _toint(before), _toint(after)

    if after == 0:
        section = raw[before:]
    else:
        section = raw[before:-after]
    return cls(section)


def _read_json_number(_string: str) -> float | int:
    ret = ''

    minus = _string[0] == '-'
    if minus:
        ret += '-'
        _string = _string[1:]

    def read_fraction(sub: str):
        sub_ret = ''
        if sub[0] == '.':
            sub_ret += '.'
            sub = sub[1:]
            while sub[0] in DIGITS:
                sub_ret += sub[0]
                sub = sub[1:]

        return sub_ret, sub

    def read_exponent(sub: str):
        sub_ret = ''
        if sub[0].lower() == 'e':
            sub_ret += sub[0]
            sub = sub[1:]

            if sub[0] in "-+":
                sub_ret += sub[0]
                sub = sub[1:]

            if sub[0] not in DIGITS:
                raise exceptions.UnclosedJSONError(f"Invalid exponent {sub}")

            while sub[0] in DIGITS:
                sub_ret += sub[0]
                sub = sub[1:]

        return sub_ret

    if _string[0] == '0':
        ret += '0'
        _string = _string[1:]

    elif _string[0] in DIGITS[1:9]:
        while _string[0] in DIGITS:
            ret += _string[0]
            _string = _string[1:]

    frac, _string = read_fraction(_string)
    ret += frac

    ret += read_exponent(_string)

    return json.loads(ret)


def consume_json(_string: str, i: int = 0) -> str | float | int | dict | list | bool | None:
    """
    Reads a JSON string and stops at the natural end (i.e. when brackets close, or when quotes end, etc.)
    """
    # Named by ChatGPT
    section = _string[i:]
    if section.startswith("true"):
        return True
    elif section.startswith("false"):
        return False
    elif section.startswith("null"):
        return None
    elif section[0] in "0123456789.-":
        return _read_json_number(section)

    depth = 0
    json_text = ''
    out_string = True

    for char in section:
        json_text += char

        if char == '"':
            if len(json_text) > 1:
                unescaped = json_text[-2] != '\\'
            else:
                unescaped = True
            if unescaped:
                out_string ^= True
                if out_string:
                    depth -= 1
                else:
                    depth += 1

        if out_string:
            if char in "[{":
                depth += 1
            elif char in "}]":
                depth -= 1

        if depth == 0 and json_text.strip():
            try:
                return json.loads(json_text.strip())
            except Exception as e:
                warnings.warn(f"Failed to decode: {json_text.strip()!r}")
                raise e

    raise exceptions.UnclosedJSONError(f"Unclosed JSON string, read {json_text}")


def generate_page_range(limit: int, offset: int, items_per_page: int, starting_page: int = 1) -> tuple[
    range, list[int]]:
    """
    Returns a page range (and first indexes per page) generated from a page range
    :param limit: How many items to reach up to
    :param offset: Starting item idx
    :param items_per_page: Number of items per page
    :param starting_page: Page with index '0' (usually 1 actually)
    :return: tuple of page range and list of starting indexes for each page
    """

    if offset < 0:
        raise ValueError(f"offset {offset!r} < 0")
    if limit < 0:
        raise ValueError(f"limit {limit!r} < 0")

    # There are n items on display per page
    # So the first page you need to view is {page 1 idx} + {offset} // {n}

    # The final item to view is at idx {offset} + {limit} - 1
    # (You have to -1 because the index starts at 0)
    # So the page number for this is 1 + (offset + limit - 1) // n

    # But this is a range so we have to add another 1 for the second argument

    page_range = range(
        starting_page + offset // items_per_page,
        1 + starting_page + (offset + limit - 1) // items_per_page
    )
    # start_idxs = [offset] + [0] * (limit // items_per_page)

    return (
        page_range,
        # start_idxs
        [items_per_page * (i - starting_page) for i in page_range]
    )


def find_links(soup: BeautifulSoup) -> list[str]:
    ret = []
    for elem in soup.find_all("a"):
        if "href" in elem.attrs:
            ret.append(str(elem.attrs["href"]))
    return ret


def to_dformat(date: datetime, sep: str = '-') -> str:
    """
    Convert a datetime to the format dd-mm-yyyy
    """

    def i2zs(v: int):
        """convert an integer to a fixed 2-digit string"""
        return str(v).zfill(2)

    return f"{i2zs(date.month)}{sep}{i2zs(date.day)}{sep}{date.year}"


def keep_chrs(_string: str, chars=string.digits, cls: type = str):
    """
    Filter a string to only the characters provided. By default, only keeps digits
    """
    return cls(''.join(filter(
        lambda c: c in chars, _string
    )))


def slice_to_range(slc: slice) -> range:
    return range(*(arg for arg in (slc.start, slc.stop, slc.step) if arg is not None))


def get_mode_attr(attr: str, objs: list[Any]) -> tuple[bool, Any]:
    """
    Calculate the mode value of the attribute `attr`
    :param attr: attribute name
    :param objs: object list with attribute `attr`
    :return: success bool, then mode value
    """
    counts = []
    for obj in objs:
        if hasattr(obj, attr):
            this_value = getattr(obj, attr)

            for i, (value, count) in enumerate(counts):
                if value == this_value:
                    counts[i][1] += 1
                    break
            else:
                counts.append([this_value, 1])

    if counts:
        return True, max(counts, key=lambda x: x[1])[0]
    else:
        return False, None


def get_mode(objs: list[Any], no_dunder: bool = False):
    """
    Generate an object whose attributes are each a mode value of the inputted objects
    :param objs:
    :param no_dunder: whether to ignore __dunder__ attributes
    """
    if not objs:
        return None

    attrs = {}
    for attr in dir(objs[0]):
        if no_dunder and attr.startswith('__') and attr.endswith('__'):
            continue

        success, mode_attr = get_mode_attr(attr, objs)
        if success:
            try:
                mode_attr = copy.deepcopy(mode_attr)
            except Exception as e:
                warnings.warn(f"Could not deepcopy {mode_attr}.\nMaybe try setting `no_dunder` to True? Exception: {e}")
            attrs[attr] = mode_attr

    ret = object.__new__(type(objs[0]))
    ret.__dict__.update(attrs)
    return ret


def eval_inputs(soup: BeautifulSoup) -> dict[str, Any]:
    qs = {}

    # Parse inputs
    for _input in soup.find_all("input"):
        qs[_input.get("name")] = _input.get("value")

    # Parse select elements
    for select in soup.find_all("select"):
        options = select.find_all("option")

        # If there's no predefined value just pick the first
        selected_id = select.get("selected")
        selected = None
        for option in options:
            if not selected:
                if selected_id is not None:
                    if option.text == selected_id:
                        selected = option
                else:
                    selected = option

        qs[select.get("name")] = selected.get("value")

    return qs


def with_kwargs(cls):
    """
    Decorator for dataclasses to add a 'from_kwargs' method that ignores invalid kwargs

    for type hinting, add

    @classmethod
    def from_kwargs(cls, **kwargs) -> Self: ...
    """

    def from_kwargs(**kwargs):
        return cls(**{k: v for k, v in kwargs.items() if k in signature(cls).parameters})

    cls.from_kwargs = from_kwargs
    return cls
