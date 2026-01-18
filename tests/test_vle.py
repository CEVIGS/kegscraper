import os
import asyncio
from kegscraper import vle


async def test_vle():
    sess = await vle.login(
        os.environ["KEGSCRAPER_USERNAME"], os.environ["KEGSCRAPER_SECRET"]
    )
    print(
        await sess.webservice(
            "core_user_get_users_by_field",
            field="id",
            values=[i for i in range(4050, 4060)],
        )
    )


if __name__ == "__main__":
    asyncio.run(test_vle())
