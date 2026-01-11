from kegscraper import bromcom
import os


def test_b_timetable():
    sess = bromcom.login(
        int(os.environ["BID"]), os.environ["BUSER"], os.environ["BPASS"]
    )

    print(sess.email)


if __name__ == "__main__":
    test_b_timetable()
