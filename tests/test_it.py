import asyncio
from kegscraper import it


async def test_it():
    ap = [it.get_article_by_id(i) for i in range(100)]
    for a in ap:
        resp = await a
        if resp:
            print(resp)


if __name__ == "__main__":
    asyncio.run(test_it())
