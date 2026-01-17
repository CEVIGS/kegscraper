from kegscraper import bromcom
import os


def test_b_timetable():
    sess = bromcom.login(
        int(os.environ["BSCRT_ID"]), os.environ["BSCRT_UN"], os.environ["BSCRT_PW"]
    )

    print(sess.email)


if __name__ == "__main__":
    test_b_timetable()
