import os
import asyncio
from kegscraper import vle


async def test_vle():
    sess = await vle.login(
        os.environ["KEGSCRAPER_USERNAME"], os.environ["KEGSCRAPER_SECRET"]
    )
    print(await sess.connect_notifications())


if __name__ == "__main__":
    asyncio.run(test_vle())
