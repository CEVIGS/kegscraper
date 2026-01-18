# development

Here is some information which will help you to develop/contribute to kegscraper

## prerequisites

- [uv](https://github.com/astral-sh/uv)
- python 3.10 or higher (installable via uv): `uv python install 3.10`
- [git](https://git-scm.com)
- a [github](https://github.com) account

## steps

1. [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) the [kegscraper repo](https://github.com/CEVIGS/kegscraper)
2. clone that repo. Copy the url of your repo and run `git clone {url}`
3. run `uv venv`
4. On windows (pwsh), run `.venv/Scripts/activate`, on mac/liunux, run `source .venv/bin/activate`
5. Run `uv sync`
6. Test your code. Make a directory: `tests/local_tests` and put your code there.
  - The `tests/` directory hosts scripts which can be run with [`pytest`](https://docs.pytest.org/en/stable/).
7. When you have added your feature or hotfix, open a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
8. Wait/hope for it to be merged!

