import time

import schedule

from baha_auto_lottery.auto_check_in import run_check_in
from baha_auto_lottery.auto_lottery_hu import run_lottery


def background_baha():
    print("開始自動登入驗證")
    run_check_in()
    time.sleep(120)
    print("結束登入")
    print("開始自動抽獎")
    run_lottery()


if __name__ == '__main__':
    schedule.every().day.at("05:00").do(background_baha)
    while True:
        schedule.run_pending()
        time.sleep(1)
