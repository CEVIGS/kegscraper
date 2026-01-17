import asyncio
import os

from kegscraper import kerboodle


async def test_kerboodle():
    sess = await kerboodle.login(
        os.environ["KINSTITUTION"], os.environ["KUSER"], os.environ["KPASS"]
    )
    for course in await sess.connect_courses():
        print(await course.digital_books)


if __name__ == "__main__":
    asyncio.run(test_kerboodle())
