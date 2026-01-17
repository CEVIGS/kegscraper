from kegscraper import bromcom
import os
import asyncio
from pprint import pprint


async def test_b_timetable():
    sess = await bromcom.login(
        int(os.environ["BSCRT_ID"]), os.environ["BSCRT_UN"], os.environ["BSCRT_PW"]
    )

    print(await sess.email)
    print(sess.username)

    pfp, _ = (
        await sess.school_photo
    )  # the ext provided by content-disposition (png) is wrong. so dont use ext
    with open("school_photo.gif", "wb") as f:
        f.write(pfp)

    pfp, ext = await sess.pfp
    with open(f"pfp{ext}", "wb") as f:
        f.write(pfp)

    # pprint(await sess.school_contact_details)
    # pprint(await sess.get_timetable_list())
    # pprint(await sess.get_weeks_a_b(5))
    # pprint(await sess.get_mode_timetables())
    # print(await sess.present_late_ratio)
    print(await sess.attendance_status)


if __name__ == "__main__":
    asyncio.run(test_b_timetable())
