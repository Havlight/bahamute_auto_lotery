import datetime
import logging
import random
import string
import sys
import time

import pytz
from flask import Flask
from flask import render_template, redirect, session, request
import schedule
import threading
from baha_auto_lottery.auto_check_in import run_check_in
from baha_auto_lottery.auto_lottery_hu import run_lottery, handler
from baha_auto_lottery.config import config

def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


def convert_to_local_time(eight_timezone, hour, minute):
    eight_tz = pytz.timezone(eight_timezone)
    eight_time = datetime.datetime.now(tz=eight_tz).replace(hour=hour, minute=minute, second=0)
    local_time = eight_time.astimezone(local_timezone)
    return local_time.strftime("%H:%M")


scheduled_time = "尚未設定"
app = Flask(__name__)
app.config['SECRET_KEY'] = "ALkxLAxkJJJJ"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == config['account']['username'] and password == config['account']['password']:
            session['is_login'] = "True"
            return render_template('login.html', login_msg="登入成功")
        else:
            return render_template('login.html', login_msg="登入失敗")

    if 'is_login' in session and session['is_login'] == "True":
        return render_template('login.html', login_msg="已登入")
    else:
        return render_template('login.html', login_msg="尚未登入")


@app.route('/', methods=['GET', 'POST'])
def index():
    global scheduled_time
    if 'is_login' in session and session['is_login'] == "True":
        if request.method == 'GET':
            return render_template('index.html', scheduled_time=scheduled_time)
        elif request.method == 'POST':

            hour = request.form['hour']
            minute = request.form['minute']

            if len(hour) != 2 or len(minute) != 2:
                return render_template('index.html', scheduled_time=scheduled_time + " 格式錯誤")
            if not (hour.isdigit() and minute.isdigit()):
                return render_template('index.html', scheduled_time=scheduled_time + " 非數字")
            if int(hour) > 24 or int(minute) > 60:
                return render_template('index.html', scheduled_time=scheduled_time + " 錯誤時間")
            local_time = convert_to_local_time("Asia/Shanghai", int(hour), int(minute))
            scheduled_time = local_time
            schedule.clear()
            schedule.every().day.at(scheduled_time).do(background_baha)
            return render_template('index.html',
                                   scheduled_time="local:" + scheduled_time,
                                   timezone="timezone:" + local_timezone.__str__())
    else:
        return redirect('/login')


@app.route('/logout')
def logout():
    if 'is_login' in session and session['is_login'] == "True":
        session.clear()
        return redirect('/login')
    else:
        return redirect('/login')


def background_baha():
    print("開始自動登入驗證")
    run_check_in()
    time.sleep(5)
    print("結束登入")
    print("開始自動抽獎")
    run_lottery()


def job():
    while True:
        schedule.run_pending()
        time.sleep(1)


background_thread = threading.Thread(target=job)
background_thread.start()

app.logger.addHandler(handler)
app.logger.addHandler(logging.StreamHandler(stream=sys.stdout))
app.logger.setLevel(logging.DEBUG)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    app.run()
