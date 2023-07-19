import asyncio
import random
import re
import sys
import time
from random import randint
from playwright.async_api import async_playwright
import logging
import httpx
import traceback
import os
from baha_auto_lottery.config import config
from playwright_stealth import stealth_async

FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO)
handler = logging.FileHandler('gamer.log', 'a+', 'utf-8')
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(FORMAT))

logging.info('正在初始化')


async def main():
    async def login():
        data = {
            'uid': config['account']['username'],
            'passwd': config['account']['password'],
            'vcode': '7045'
        }
        sess.headers.update(
            {
                'user-agent': 'Bahadroid (https://www.gamer.com.tw/)',
                'x-bahamut-app-instanceid': 'cc2zQIfDpg4',
                'x-bahamut-app-android': 'tw.com.gamer.android.activecenter',
                'x-bahamut-app-version': '251',
                'content-type': 'application/x-www-form-urlencoded',
                'accept-encoding': 'gzip',
                'cookie': 'ckAPP_VCODE=7045'
            },
        )
        account = sess.post(
            'https://api.gamer.com.tw/mobile_app/user/v3/do_login.php', data=data)
        account_f = account.json()
        if account.status_code != 200:
            logging.error('登入失敗')
            sys.exit(0)
        logging.info('登入成功！')
        logging.info(f'您好：{account_f["nickname"]}')
        sess.headers = {
            'user-agent': config['User-Agent'],
        }

        for _key, _value in sess.cookies.items():
            await context.add_cookies([{'name': _key, 'value': _value, 'domain': '.gamer.com.tw', 'path': '/'}])

    async def check_lottery():
        req = sess.get('https://fuli.gamer.com.tw/shop.php')
        lottery_page = int(re.findall(r'page=(\d)&history=0', req.text)[0])
        for page in range(1, lottery_page + 1):
            req = sess.get(
                f'https://fuli.gamer.com.tw/shop.php?page={page}&history=0')
            for _sn in re.findall(r'shop_detail\.php\?sn=(\d*)', req.text):
                req = sess.get(
                    f'https://fuli.gamer.com.tw/shop_detail.php?sn={_sn}')
                if req.text.find('question-popup') == -1:
                    answer = []
                else:
                    answer = re.findall(
                        r'data-question=\"(\d)\".*data-answer=\"(\d)\"', req.text)
                    answer_dict = {}
                    for _question, _answer in answer:
                        answer_dict[_question] = _answer
                    answer = ' '.join(_ for _ in answer_dict.values())
                title = re.findall(r'<h1>(.*)</h1>', req.text)[0]
                if req.text.find('抽抽樂') != -1 and req.text.find('本日免費兌換次數已用盡') == -1:
                    logging.info(f"已將 {title} 新增到抽獎隊列中")
                    await lottery(_sn, answer, title)

    async def simulate_human_delay():
        delay = random.uniform(1, 3)  # 随机生成 0.5 到 1.5 秒之间的延迟时间
        await asyncio.sleep(delay)

    async def simulate_page_mouse():
        for _ in range(3):
            # 生成随机移动的坐标
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            # 模拟鼠标移动到指定坐标
            await page.mouse.move(x, y)
            await simulate_human_delay()

    async def simulate_page_scroll():
        # 模拟随机滚动页面
        for _ in range(3):
            # 随机生成滚动的距离
            scroll_amount = random.randint(100, 500)
            # 模拟页面滚动
            await page.mouse.wheel(0, scroll_amount)
            # 添加随机延迟
            await simulate_human_delay()

    async def answer_lottery_question(sn):
        try:
            await page.goto(f"https://fuli.gamer.com.tw/shop_detail.php?sn={sn}")
            await simulate_page_mouse()
            await simulate_page_scroll()
            await page.get_by_text(text='看廣告免費兌換').click(delay=randint(1, 3) * 100)
            await page.locator('div.fuli-option-box > a.btn-base.fuli-option').is_visible(
                timeout=randint(3, 6) * 1000)
            try:
                while await page.locator('#dialogify_1').count():
                    for qus in await page.locator('div.fuli-option-box > a.btn-base.fuli-option').all():
                        await simulate_page_mouse()
                        await qus.click(delay=randint(1, 3) * 100)
            except:
                logging.info("回答結束")
                await page.evaluate('buyItem(1);')
        except:
            logging.info('不需要回答問題')

    async def lottery(sn, answer, title):
        global iframe
        if answer:
            req = sess.get(
                f'https://fuli.gamer.com.tw/ajax/getCSRFToken.php?_={int(time.time() * 1000)}')
            data = {
                'sn': sn,
                'token': req.text,
                'answer[]': answer
            }
            req = sess.post(
                'https://fuli.gamer.com.tw/ajax/answer_question.php', data=data)
            logging.debug(req.json())
        for _ in range(1, 11):

            if _ == 1:
                logging.info("確認是否需要回答問題")
                await answer_lottery_question(sn)

            req = sess.get(f'https://fuli.gamer.com.tw/shop_detail.php?sn={sn}')
            if req.text.find('本日免費兌換次數已用盡') != -1:
                logging.warning(f'{title} 已無免費次數')
                break
            logging.info(f'{title} 正在觀看第 {_} 次廣告')
            req = sess.get(
                f'https://fuli.gamer.com.tw/ajax/check_ad.php?area=item&sn={sn}')
            await asyncio.sleep(30)
            req = sess.get(
                f'https://fuli.gamer.com.tw/ajax/getCSRFToken.php?_={int(time.time() * 1000)}')
            finish_ad = {
                'token': req.text,
                'area': 'item',
                'sn': sn
            }
            req = sess.post(
                'https://fuli.gamer.com.tw/ajax/finish_ad.php', data=finish_ad)
            logging.info(f"{title} 廣告觀看成功")

            await page.goto(f'https://fuli.gamer.com.tw/buyD.php?ad=1&sn={sn}')
            await simulate_page_scroll()
            await page.locator("#buyD > div.flex-center.agree-confirm > div > label").click(delay=randint(1, 3) * 100)
            await simulate_page_mouse()
            await page.locator(".c-primary").click(delay=randint(1, 3) * 100)
            await simulate_page_mouse()
            await page.locator('//button[@type="submit"]').click(delay=randint(1, 3) * 100)
            await simulate_page_mouse()
            current_url = page.url
            try:
                iframe = None
                # 检查是否存在 title 为 "recaptcha challenge expires in two minutes" 的 iframe
                if await page.wait_for_selector('//iframe[@title="recaptcha challenge expires in two minutes"]',
                                                timeout=randint(3, 6) * 2000,
                                                state='visible'):
                    # 切换到该 iframe
                    iframe = page.frame_locator('//iframe[@title="recaptcha challenge expires in two minutes"]')
                    # 检查是否存在 class 为 "button-holder help-button-holder" 的 div 元素
                    click_count = 0
                    while await iframe.locator('//div[@class="button-holder help-button-holder"]').is_visible(
                            timeout=randint(3, 6) * 2000) and click_count < 10:
                        await iframe.locator('//div[@class="button-holder help-button-holder"]').click(
                            timeout=randint(3, 6) * 2000, delay=randint(1, 3) * 100)
                        await asyncio.sleep(randint(2, 4))
                        click_count += 1

                await page.wait_for_url(lambda url: url != current_url, timeout=8000)
            except Exception:
                await page.screenshot(path="出現例外狀況的頁面.png")
                try:
                    if iframe:
                        await iframe.locator('//*[@id="reset-button"]').click(delay=randint(1, 3) * 100)
                except:
                    traceback.print_exc()
                logging.info(f'{title}有可能發生例外或未跳出recaptcha(可喜可賀) 休息5到10秒')
                await asyncio.sleep(randint(5, 10))

            if page.url.find('message_done') != -1:
                logging.info(f'{title} 廣告抽獎卷成功')
                logging.info(f'{title} 休息30秒')
                await asyncio.sleep(30 + 5)
            else:
                logging.error(f'{title} 廣告抽獎卷失敗')
        logging.info(f'完成 {title}')

    async with async_playwright() as p:
        path_to_extension = config['Buster_Api_extension_path']
        headers = {
            'User-Agent': config['User-Agent'],
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            # 'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            # 'Sec-Ch-Ua-Platform': '""Windows""',
            # 'Upgrade-Insecure-Requests': '1'
        }
        headless = "--headless=new"
        if config['headless'] != "True":
            headless = ""
        sess = httpx.Client()
        context = await p.chromium.launch_persistent_context(
            '',
            headless=False,
            args=[
                headless,
                f"--disable-extensions-except={os.getcwd() + path_to_extension}",
                f"--load-extension={os.getcwd() + path_to_extension}",
                "--disable-blink-features=AutomationControlled",
                '--disable-dev-shm-usage',
                '--no-sandbox',
                # "--auto-open-devtools-for-tabs"
            ],
            user_agent=config['User-Agent'],
            ignore_https_errors=True,
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        await page.set_extra_http_headers(headers)
        await stealth_async(page)
        page.set_default_timeout(10000)
        page.set_default_navigation_timeout(5000)
        await login()
        await check_lottery()


def run_lottery():
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        input("發生錯誤\n按下 Enter 鍵以結束程式...")
