from kegscraper import bromcom
import os
import asyncio


async def test_b_timetable():
    sess = await bromcom.login(
        int(os.environ["BSCRT_ID"]), os.environ["BSCRT_UN"], os.environ["BSCRT_PW"]
    )

    print(await sess.email)
    print(sess.username)

    pfp, ext = await sess.pfp
    with open(f"idk{ext}", "wb") as f:
        f.write(pfp)


if __name__ == "__main__":
    asyncio.run(test_b_timetable())
