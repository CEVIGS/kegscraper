# kegscraper

kegscraper is a Python library for automation on the KEGS platform.
Different services used by KEGS are split into the different [submodules](/submodules.md)

## installation

### Using regular python

1. run `python3 --version`. make sure it is >=3.10.11 (older python versions are not compatible)

- you may want to set up a [venv](https://docs.python.org/3/library/venv.html)

1. run `python3 -m pip install kegscraper`
2. use `from kegscraper import it` to import a module (in this case it)

### Using uv

[uv](https://github.com/astral-sh/uv) is a pretty good tool for python and has been growing in popularity lately.
We use uv to build and publish kegscraper to pypi.

1. Make a virtualenv: `uv venv`
2. activate the virtualenv `.venv/Scripts/activate` (windows) or `source .venv/bin/activate` (mac/linux)
3. run `uv add kegscraper`
4. run `uv sync` (this isn't strictly necessary but it recommended)

## Development

See [development](/development.md)
