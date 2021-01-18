import json
import os
import sqlite3 as sql3
import time
import traceback
from datetime import datetime
from multiprocessing import Queue, Process, RLock
from threading import Thread
import requests as rq
import win32con
import win32gui

from selenium.webdriver import ActionChains
import numpy as np
from helium import *

from imge_detection import classify_png, search_box

ACC_Q = Queue(0)  # 账号验证添加
TASK_Q = Queue(0)
INFO_Q = Queue(0)
lock = RLock()
T = None


def ease_out_quad(x):
    return 1 - (1 - x) * (1 - x)


def ease_out_quart(x):
    return 1 - pow(1 - x, 4)


def ease_out_expo(x):
    if x == 1:
        return 1
    else:
        return 1 - pow(2, -10 * x)


def get_tracks(distance, seconds, ease_func):
    tracks = [0]
    offsets = [0]
    for t in np.arange(0.0, seconds, 0.1):
        ease = globals()[ease_func]
        offset = round(ease(t / seconds) * distance)
        tracks.append(offset - offsets[-1])
        offsets.append(offset)
    return offsets, tracks


def drag_and_drop(browser, offset):
    knob = browser.find_element_by_css_selector("#test")
    offsets, tracks = get_tracks(offset, 2, 'ease_out_expo')
    ActionChains(browser).click_and_hold(knob).perform()
    for x in tracks:
        ActionChains(browser).move_by_offset(x, 0).perform()
    ActionChains(browser).pause(0.5).release().perform()
    return browser


def close_info(driver):
    try:
        driver.find_element_by_css_selector('.close').click()
    except:
        pass
    try:
        driver.find_element_by_css_selector('.svg-close').click()
    except:
        pass
    try:
        driver.find_element_by_css_selector('.svg-cancel').click()
    except:
        pass
    try:
        click(Text('确认'))
    except:
        pass
    return driver


def disable(qcls):
    qcls.setEnabled(False)


def mtd_run(kwargs):
    try:
        while c := kwargs["ACC_Q"].get(block=True):
            print(kwargs["id"] + " . ", c)
            kwargs["WORKING_TASK"].append(c["acc"])
            a = start_firefox('http://mp.iqiyi.com', headless=True)
            a.maximize_window()
            wait_until(Text('登录').exists)
            # s.emit({"thread_id": int(kwargs["id"]), "process": "正在登录...", "acc": c["acc"]})
            kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "正在登录...", "acc": c["acc"]})
            while True:
                count = 0
                try:
                    count += 1
                    click(Text('登录'))
                    wait_until(Text('账号密码登录').exists, timeout_secs=10)
                    click(Text('账号密码登录'))
                    wait_until(TextField('请输入密码').exists)
                    break
                except:
                    if count > 5:
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": "验证失败...", "acc": c["acc"]})
                        kwargs["WORKING_TASK"].remove(c["acc"])
                        a.quit()
                        continue
                    pass
            time.sleep(1)
            try:
                write(c["acc"], TextField('请输入手机号或邮箱'))
                write(c["psd"], TextField('请输入密码'))
            except:
                kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "账号密码输入错误...", "acc": c["acc"]})
            time.sleep(2)
            try:
                a.find_element_by_css_selector('.btn-login').click()
            except:
                pass
            kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "正在验证...", "acc": c["acc"]})
            while True:
                try:
                    wait_until(Text('向右滑动滑块填充拼图').exists, timeout_secs=30)
                    time.sleep(0.5)
                    a.find_element_by_tag_name('canvas').screenshot(f'{os.getpid()}.png')
                    time.sleep(0.5)
                    sl = classify_png(f'./{os.getpid()}.png', 'D://iqiyi//out/pngs.pk')
                    box = search_box('D://iqiyi//out//' + sl[0], f'./{os.getpid()}.png')
                    a = drag_and_drop(a, box[0])
                    time.sleep(2)
                    if Text('向右滑动滑块填充拼图').exists():
                        a.find_element_by_css_selector('.refresh').click()
                        continue
                    a = close_info(a)
                    wait_until(Text('主页').exists, timeout_secs=30)
                    break
                except Exception as e:
                    traceback.print_exc()
                    try:
                        if Text("主页").exists():
                            break
                    except:
                        pass
                    kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "验证失败...", "acc": c["acc"]})
                    kwargs["WORKING_TASK"].remove(c["acc"])
                    a.quit()
                    continue
            try:
                wait_until(Text('主页').exists, timeout_secs=30)
                a = close_info(a)
                plus = 0
                cols = list([])
                time.sleep(0.3)
                click(Text("发布作品"))
                time.sleep(1.5)
                if Text('拖拽视频到此处也可上传视频到合集PLUS').exists():
                    plus = 1
                    kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "有专辑...", "acc": c["acc"]})
                    click(Text("作品管理"))
                    time.sleep(1)
                    click(Text("合集管理"))
                    time.sleep(1)
                    leng = -1
                    while leng != len(cols):
                        leng = len(cols)
                        col = a.find_elements_by_css_selector(".base-management-title")
                        label = a.find_elements_by_css_selector(".base-label")
                        for ind, cl in enumerate(col):
                            index = 0 if ind == 0 else 2 * ind
                            cols.append(cl.text + f"><{label[index].text}><{label[index + 1].text}")
                        scroll_down(3000)
                        cols = list(set(cols))
                        if Text("下一页").exists():
                            click(Text("下一页"))
                            time.sleep(1)
                    print(cols)
                js = "document.getElementsByClassName('aside-inner')[0].scrollTop=1000"
                a.execute_script(js)
                click(Text('账号设置'))
                a = close_info(a)
                wait_until(Text('爱奇艺号信息').exists, timeout_secs=30)
                time.sleep(0.3)
                kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "获取账号信息...", "acc": c["acc"]})
                time.sleep(0.3)
                con = a.find_elements_by_css_selector('.account-item-con')
                nick = con[0].text
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"昵称 : {nick}...", "acc": c["acc"]})
                uid = con[3].text
                a.find_element_by_css_selector(".account-headImg").screenshot(f"./icon/{nick}.png")
                icon = f"./icon/{nick}.png"
                time.sleep(0.3)
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"UID : {uid}...", "acc": c["acc"]})
                js = "document.getElementsByClassName('aside-inner')[0].scrollTop=150"
                a.execute_script(js)
                click(Text('等级权益'))
                time.sleep(2)
                wait_until(Text('我的等级').exists)
                time.sleep(2)
                lv = a.find_element_by_css_selector('.lev-num').text.split('.')[1]
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"等级 : Lv{lv}...", "acc": c["acc"]})
                click(Text('信用分'))
                time.sleep(2)
                record = a.find_elements_by_css_selector('.green')[0].text[:-1]
                cookies = a.get_cookies()
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": "", "cookies": json.dumps(cookies), "acc": c['acc']})
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"信用分 : {record}...", "acc": c["acc"]})
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "lv": lv, "record": record, "nick": nick, "plus": plus, "uid": uid,
                     "icon": icon, "psd": c["psd"], "process": f"", "acc": c["acc"], "cols": ";".join(cols),
                     "cookies": json.dumps(cookies)})
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"账号信息搜集完成...", "acc": c["acc"]})
                a.quit()
                kwargs["WORKING_TASK"].remove(c["acc"])
            except:
                traceback.print_exc()
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"搜集失败...", "acc": c["acc"]})
                kwargs["WORKING_TASK"].remove(c["acc"])
                a.quit()
    except:
        traceback.print_exc()


class Sql():
    sql = None
    instance = None
    SQL_Q = None
    init_ret = None

    def __new__(cls, *args, **kwargs):
        if Sql.instance is None:
            Sql.instance = object.__new__(cls)
        return Sql.instance

    def __init__(self):
        self.t = Thread(target=self.run)
        self.t.setDaemon(True)
        self.t.start()
        self.SQL_Q = Queue(0)

    def run(self):
        try:
            self.sql = sql3.connect("sc.sqlite3")
            ret = self.sql.execute("""
                        CREATE TABLE IF NOT EXISTS ACC(acc char(50) primary key,psd char(50),level char(50),uid char(50),record char(50),has_plus int,icon_path char(50), nick char(50), cols char(500), cookies char(2000));
                    """)
            ret = self.sql.execute("""
                        CREATE TABLE IF NOT EXISTS DALIY(acc char(50), total_found char(50), monthly_found char(50), last_found char(50), total_pv char(50), last_pv char(50), date_time char(50), primary key(acc, date_time));
                    """)
            self.sql.commit()
        except:
            traceback.print_exc()
        while s := self.SQL_Q.get(block=True):
            try:
                if s == "SELECT * FROM ACC;":
                    ret = self.sql.execute(s)
                    self.sql.commit()
                    self.init_ret = list(ret)
                try:
                    self.sql.execute(s)
                    self.sql.commit()
                    print("commit : ", s)
                except:
                    pass
            except:
                traceback.print_exc()

    def add_sql(self, sql):
        print("add : ", sql)
        self.SQL_Q.put_nowait(sql)

    def __del__(self):
        print("del : sql")
        self.sql.close()


def login_acc(acc, psd, cookies):
    global T
    T = Process(target=th, args=(acc, psd, cookies,))
    T.daemon = True
    T.start()


def th(acc, psd, cookies):
    a = start_firefox('http://mp.iqiyi.com', headless=False)
    a.maximize_window()
    if cookies:
        try:
            for c in json.loads(cookies):
                a.add_cookie(c)
            go_to('http://mp.iqiyi.com')
            wait_until(Text("发布作品").exists, timeout_secs=5)
            return
        except:
            traceback.print_exc()
    wait_until(Text('登录').exists)
    while True:
        count = 0
        try:
            count += 1
            click(Text('登录'))
            wait_until(Text('账号密码登录').exists, timeout_secs=10)
            click(Text('账号密码登录'))
            wait_until(TextField('请输入密码').exists)
            break
        except:
            if count > 5:
                a.quit()
                return
            pass
    time.sleep(1)
    write(acc, TextField('请输入手机号或邮箱'))
    write(psd, TextField('请输入密码'))
    time.sleep(2)
    try:
        a.find_element_by_css_selector('.btn-login').click()
    except:
        pass
    while True:
        try:
            wait_until(Text('向右滑动滑块填充拼图').exists, timeout_secs=30)
            time.sleep(0.5)
            a.find_element_by_tag_name('canvas').screenshot(f'{os.getpid()}.png')
            time.sleep(0.5)
            sl = classify_png(f'./{os.getpid()}.png', 'D://iqiyi//out/pngs.pk')
            box = search_box('D://iqiyi//out//' + sl[0], f'./{os.getpid()}.png')
            a = drag_and_drop(a, box[0])
            time.sleep(2)
            if Text('向右滑动滑块填充拼图').exists():
                a.find_element_by_css_selector('.refresh').click()
                continue
            a = close_info(a)
            wait_until(Text('主页').exists, timeout_secs=30)
            break
        except Exception as e:
            traceback.print_exc()
            if Text("主页").exists():
                break
            a.quit()
            return


def is_quit(acc, kwargs):
    if acc in kwargs["QUIT_L"]:
        try:
            print('移除取消队列 - ', acc)
            kwargs["WORKING_TASK"].remove(acc)
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"取消任务...", "acc": acc})
            return 1
        except:
            pass
    return 0


def task_run(kwargs):
    while t := kwargs["TASK_Q"].get(block=True):
        try:
            a.quit()
        except:
            pass
        print("开始 ", t)
        acc = t[0]
        if is_quit(acc, kwargs):
            a.quit()
            kwargs["QUIT_L"].remove(acc)
            continue
        quit = 0
        psd = t[1]
        kwargs["WORKING_TASK"].append(acc)
        a = start_firefox('http://mp.iqiyi.com', headless=False)
        a.maximize_window()
        login = 0
        cookies = t[3]
        if cookies:
            try:
                for c in json.loads(cookies):
                    a.add_cookie(c)
                go_to('http://mp.iqiyi.com')
                wait_until(Text("发布作品").exists, timeout_secs=5)
                login = 1
            except:
                traceback.print_exc()
        if not login:
            confirm = 1
            wait_until(Text('登录').exists)
            kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "正在登录...", "acc": acc})
            while True:
                count = 0
                try:
                    count += 1
                    time.sleep(1)
                    click(Text('登录'))
                    wait_until(Text('账号密码登录').exists, timeout_secs=30)
                    click(Text('账号密码登录'))
                    wait_until(TextField('请输入密码').exists)
                    break
                except:
                    if count > 3:
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": "验证失败...", "acc": acc})
                        try:
                            kwargs["WORKING_TASK"].remove(acc)
                        except:
                            pass
                        a.quit()
                        confirm = 0
                    try:
                        time.sleep(1)
                        a.find_element_by_css_selector(".frame-close").click()
                    except:
                        pass
            time.sleep(1)
            if not confirm:
                continue
            try:
                wait_until(TextField('请输入手机号或邮箱').exists, timeout_secs=4)
                write(acc, TextField('请输入手机号或邮箱'))
                write(psd, TextField('请输入密码'))
            except:
                a.quit()
                try:
                    kwargs["WORKING_TASK"].remove(acc)
                except:
                    pass
                continue
            time.sleep(2)
            try:
                a.find_element_by_css_selector('.btn-login').click()
            except:
                pass
            kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "正在验证...", "acc": acc})
            c = 0
            while True:
                try:
                    wait_until(Text('向右滑动滑块填充拼图').exists, timeout_secs=30)
                    time.sleep(0.5)
                    a.find_element_by_tag_name('canvas').screenshot(f'{os.getpid()}.png')
                    time.sleep(0.5)
                    sl = classify_png(f'./{os.getpid()}.png', 'D://iqiyi//out/pngs.pk')
                    box = search_box('D://iqiyi//out//' + sl[0], f'./{os.getpid()}.png')
                    if is_quit(acc, kwargs):
                        confirm = 0
                        kwargs["QUIT_L"].remove(acc)
                        break
                    a = drag_and_drop(a, box[0])
                    time.sleep(2)
                    if Text('向右滑动滑块填充拼图').exists():
                        a.find_element_by_css_selector('.refresh').click()
                        continue
                    a = close_info(a)
                    wait_until(Text('主页').exists, timeout_secs=30)
                    break
                except Exception as e:
                    c += 1
                    traceback.print_exc()
                    try:
                        if Text("主页").exists():
                            break
                    except:
                        pass
                    kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": "验证失败...", "acc": acc})
                    try:
                        kwargs["WORKING_TASK"].remove(acc)
                    except:
                        pass
                    if c > 10:
                        confirm = 0
                        a.quit()
                        break
            if not confirm:
                a.quit()
                continue
            cookies = a.get_cookies()
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": "", "cookies": json.dumps(cookies), "acc": acc})
        for v in t[2]:
            if is_quit(acc, kwargs):
                quit = 1
                kwargs["QUIT_L"].remove(acc)
                break
            kwargs["INFO_Q"].put_nowait({"thread_id": int(kwargs["id"]), "process": f"发布..{v['vpath']}", "acc": acc})
            v["vpath"] = v["vpath"].replace('/', '\\')
            a = close_info(a)
            time.sleep(1)
            c = 0
            while True:
                try:
                    c += 1
                    if is_quit(acc, kwargs):
                        quit = 1
                        break
                    kwargs["INFO_Q"].put_nowait(
                        {"thread_id": int(kwargs["id"]), "process": f"点击发布作品...{c}", "acc": acc})
                    wait_until(Text('发布作品').exists, timeout_secs=1)
                    click(Text('发布作品'))
                    if Text('确认').exists():
                        click(Text('确认'))
                    wait_until(Text('上传视频').exists)
                    break
                except:
                    time.sleep(0.5)
                    if c > 5:
                        break
                    refresh()
                    time.sleep(1.5)
            if quit:
                break
            try:
                if v["col"] != "单个视频" and Text('上传视频到合集').exists():
                    if Text('上传视频到合集').exists():
                        try:
                            drag_file(v["vpath"], to=Text('拖拽视频到此处也可上传视频到合集PLUS'))
                        except:
                            continue
                        wait_until(Text('新建合集').exists)
                        time.sleep(2)
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"搜索专辑-{v['col']}...", "acc": acc})
                        write(v['col'], TextField('搜索合集'))
                        a.find_element_by_css_selector('.searchBtn').click()
                        time.sleep(2)
                        try:
                            p = a.find_elements_by_css_selector('.tg-piclist_infoCon')[0].click()
                        except Exception as e:
                            write(' ', TextField('搜索合集'))
                            kwargs["INFO_Q"].put_nowait(
                                {"thread_id": int(kwargs["id"]), "process": f"未找到专辑...", "acc": acc})
                            a.find_element_by_css_selector('.searchBtn').click()
                            time.sleep(2)
                            p = a.find_elements_by_css_selector('.tg-piclist_infoCon')[0].click()
                        time.sleep(1)
                        click(Text('确定'))
                        wait_until(Text('基本信息').exists)
                        scroll_down(200)
                        while True:
                            try:
                                if is_quit(acc, kwargs):
                                    quit = 1
                                    break
                                a.find_elements_by_css_selector('.mp-input__inner')[0].clear()
                                a.find_elements_by_css_selector('.mp-input__inner')[0].send_keys(v["title"][:30])
                                a.find_elements_by_css_selector('.mp-input__inner')[1].click()
                                click(Text(v['cls']))
                                time.sleep(2)
                                kwargs["INFO_Q"].put_nowait(
                                    {"thread_id": int(kwargs["id"]), "process": f"选择{v['cls']}频道...", "acc": acc})
                                break
                            except:
                                pass
                        js = '''
                                    a=document.getElementsByClassName("mp-input__inner");
                                    for(let i in a){
                                        a[i].readOnly = false;
                                    }
                            '''
                        if quit:
                            break
                        a.execute_script(js)
                        tags = [i for i in v['tags'].split(';') if i]
                        tags.append('搞笑')
                        for ind, j in enumerate(tags):
                            a.find_element_by_css_selector('.mp-input__tag-inner').send_keys(j)
                            press(ENTER)
                            time.sleep(0.2)
                        scroll_down(500)
                        if v['org']:
                            try:
                                click(Text("原创"))
                                a.find_elements_by_css_selector('.mp-radio__label')[0].click()
                            except:
                                pass
                        else:
                            try:
                                click(Text("转载"))
                                a.find_elements_by_css_selector('.mp-radio__label')[1].click()
                            except:
                                pass
                        write(v['title'], TextField('请输入内容'))
                        ind = 3 if v['cls'] == '游戏' else 2
                        try:
                            a.find_elements_by_css_selector('.mp-input__inner')[ind].send_keys(v['title'][:11])
                        except:
                            a.find_elements_by_css_selector('.mp-input__inner')[ind + 1].send_keys(v['title'][:11])
                        scroll_up(3000)
                        scroll_down(270)
                        if v['cls'] == '搞笑':
                            click(Text('搞笑短片'))
                        if v['cls'] == '原创':
                            click(Text('短片'))
                            time.sleep(2)
                            click(Text('搞笑'))
                            click(Text('唯美'))
                            click(Text('配音'))
                            click(Text('剪辑'))
                        if v['cls'] == '数码':
                            click(Text('评测'))
                        if v['cls'] == '音乐':
                            click(Text('其他'))
                        if v['cls'] == '游戏':
                            click(TextField("-请选择-"))
                            time.sleep(1)
                            click(Text('网络游戏'))
                            time.sleep(1)
                            click(Text('绝地求生'))
                        scroll_up(1000)
                        scroll_down(3000)
                        if TextField('请选择时间').exists():
                            da = datetime.now().strftime('%Y%m%d')
                            write(da, TextField('请选择时间'))
                else:
                    if os.path.exists(v['vpath']):
                        drag_file(v['vpath'], to=Text('拖拽视频到此处也可上传，可同时上传'))
                    else:
                        continue
                    time.sleep(2)
                    if Text('您每日可上传').exists():
                        break
                    if TextField('请输入内容').exists():
                        a = close_info(a)
                        try:
                            wait_until(TextField('请输入内容').exists)
                        except:
                            continue
                        write(v['title'], TextField('请输入内容'))
                    a.find_elements_by_css_selector('.mp-input__inner')[0].clear()
                    a.find_elements_by_css_selector('.mp-input__inner')[0].send_keys(v["title"][:30])
                    kwargs["INFO_Q"].put_nowait(
                        {"thread_id": int(kwargs["id"]), "process": f"填写标题 {v['title']}...", "acc": acc})
                    time.sleep(2)
                    scroll_down(400)
                    if TextField('输入视频描述').exists():
                        wait_until(TextField('输入视频描述').exists)
                        write(v['title'], TextField('输入视频描述'))
                        # bug 选自分类
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"输入视频描述...", "acc": acc})
                    if (not TextField('选择分类/频道').exists()) and TextField('选择分类').exists():
                        wait_until(TextField('选择分类').exists)
                        click(TextField('选择分类'))
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"选择频道 {v['cls']}...", "acc": acc})
                        time.sleep(0.3)
                        try:
                            click(Text(v['cls']))
                        except:
                            click(Text('搞笑'))
                    tags = [i for i in v['tags'].split(' ') if i]
                    tags.append('搞笑')
                    kwargs["INFO_Q"].put_nowait(
                        {"thread_id": int(kwargs["id"]), "process": f"输入标签 {v['tags']}...", "acc": acc})
                    for ind, j in enumerate(tags):
                        a.find_element_by_css_selector('.mp-input__tag-inner').send_keys(j)
                        press(ENTER)
                        time.sleep(0.2)
                    scroll_down(500)
                    kwargs["INFO_Q"].put_nowait(
                        {"thread_id": int(kwargs["id"]), "process": f"选择是否原创 {v['org']}...", "acc": acc})
                    if v['org']:
                        try:
                            click(Text("原创"))
                            a.find_elements_by_css_selector('.mp-radio__label')[0].click()
                        except:
                            pass
                    else:
                        try:
                            click(Text("转载"))
                            a.find_elements_by_css_selector('.mp-radio__label')[1].click()
                        except:
                            pass
            except Exception as e:
                traceback.print_exc()
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"上传失败-{v['vpath']}...",
                     "vpath": v['vpath'].replace('\\', '/'),
                     "acc": acc})
                print("上传失败1")
                if Text("申请材料").exists():
                    break
                continue
            scroll_up(2000)
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"上传中...", "acc": acc})
            upload = 1
            while True:
                try:
                    if is_quit(acc, kwargs):
                        upload = 0
                        quit = 1
                        break
                    try:
                        p = a.find_element_by_css_selector(".upload-progress-percent").text
                        if Text('上传失败').exists():
                            break
                    except:
                        traceback.print_exc()
                    wait_until(Text('上传成功').exists)
                    break
                except:
                    traceback.print_exc()
                    try:
                        if p is None:
                            pass
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"上传中...{p}", "acc": acc})
                    except:
                        pass
                    if Text('上传失败').exists():
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"上传失败-{v['vpath']}...",
                             "vpath": v['vpath'].replace('\\', '/'),
                             "acc": acc})
                        a = close_info(a)
                        print("上传失败2")
                        upload = 0
                        break
                    pass
                    if Text("申请材料").exists():
                        break
            if quit:
                break
            if not upload:
                continue
            if Text('上传失败').exists():
                kwargs["INFO_Q"].put_nowait(
                    {"thread_id": int(kwargs["id"]), "process": f"上传失败-{v['vpath']}...",
                     "vpath": v['vpath'].replace('\\', '/'),
                     "acc": acc})
                print("上传失败3")
                continue
            click(Text('设置封面'))
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"设置封面...", "acc": acc})
            while True:
                try:
                    if is_quit(acc, kwargs):
                        quit = 1
                        break
                    time.sleep(2)
                    click(Text("上传图片"))
                    lock.acquire()
                    v['image'] = v['image'].replace('/', '\\')
                    dialog = win32gui.FindWindow('#32770', '文件上传')  # 对话框
                    ComboBoxEx32 = win32gui.FindWindowEx(dialog, 0, 'ComboBoxEx32', None)
                    ComboBox = win32gui.FindWindowEx(ComboBoxEx32, 0, 'ComboBox', None)
                    Edit = win32gui.FindWindowEx(ComboBox, 0, 'Edit', None)  # 上面三句依次寻找对象，直到找到输入框Edit对象的句柄
                    button = win32gui.FindWindowEx(dialog, 0, 'Button', None)  # 确定按钮Button
                    win32gui.SendMessage(Edit, win32con.WM_SETTEXT, None, os.path.abspath(v['image']))  # 往输入框输入绝对地址
                    win32gui.SendMessage(dialog, win32con.WM_COMMAND, 1, button)  # 按button
                    lock.release()
                    time.sleep(2)
                    click(Text('确认'))
                    wait_until(Text('编辑封面').exists, timeout_secs=30)
                    time.sleep(2)
                    if Text('图片上传失败').exists():
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"图片上传失败...", "acc": acc})
                    break
                except:
                    traceback.print_exc()
                    break
            if quit:
                break
            time.sleep(1)
            scroll_down(2000)
            c = 0
            while True:
                try:
                    c += 1
                    time.sleep(1)
                    if is_quit(acc, kwargs):
                        quit = 1
                        break
                    time.sleep(2)
                    click(Button('发布'))
                    time.sleep(2)
                    kwargs["INFO_Q"].put_nowait(
                        {"thread_id": int(kwargs["id"]), "process": f"点击发布...", "acc": acc})
                    break
                except:
                    if c > 5:
                        break
                    if Text("申请材料").exists():
                        kwargs["INFO_Q"].put_nowait(
                            {"thread_id": int(kwargs["id"]), "process": f"上传失败-{v['vpath']}...",
                             "vpath": v['vpath'].replace('\\', '/'),
                             "acc": acc})
                        break
                    traceback.print_exc()
            if quit:
                break
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"发布成功...", "vpath": v['vpath'].replace('\\', '/'),
                 "acc": acc})
            if Text("今日已").exists():
                a = close_info(a)
                break
            a = close_info(a)
            try:
                os.remove(v['vpath'])
            except:
                traceback.print_exc()
        try:
            if quit:
                try:
                    a.quit()
                except:
                    pass
                continue
            a = close_info(a)
            wait_until(Text('主页').exists, timeout_secs=20)
            a = close_info(a)
            click(Text('主页'))
            time.sleep(2)
            a = close_info(a)

            # TODO
            wait_until(Text('总播放量').exists, timeout_secs=20)
            print('获取昨日收益/播放量')
            total_pv = a.find_elements_by_css_selector('.data')[0].text
            pv_last = a.find_elements_by_css_selector('.num')[1].text.split(' ')[1]
            found_last = a.find_elements_by_css_selector('.num')[2].text.split(' ')[1]
            found_last = float(found_last.replace(',', '')) if (found_last != '--' and found_last != '0.00') else 0
            plus = 0
            cols = list([])
            time.sleep(0.3)
            click(Text("发布作品"))
            time.sleep(1.5)
            # TODO
            if Text('拖拽视频到此处也可上传视频到合集PLUS').exists():
                plus = 1
                click(Text("作品管理"))
                time.sleep(1)
                click(Text("合集管理"))
                time.sleep(1)
                leng = -1
                while leng != len(cols):
                    leng = len(cols)
                    col = a.find_elements_by_css_selector(".base-management-title")
                    label = a.find_elements_by_css_selector(".base-label")
                    for ind, cl in enumerate(col):
                        index = 0 if ind == 0 else 2 * ind
                        cols.append(cl.text + f"><{label[index].text}><{label[index + 1].text}")
                    scroll_down(3000)
                    cols = list(set(cols))
                    if Text("下一页").exists():
                        click(Text("下一页"))
                        time.sleep(1)
                print(cols)
            else:
                cols = ''
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"收集合集...", "cols": ";".join(cols), "acc": acc})
            js = "document.getElementsByClassName('aside-inner')[0].scrollTop=3000"
            a.execute_script(js)
            click(Text('账号设置'))
            a = close_info(a)
            wait_until(Text('爱奇艺号信息').exists, timeout_secs=20)
            print('获取账号信息')
            con = a.find_elements_by_css_selector('.account-item-con')
            nick = con[0].text
            uid = con[3].text
            click(Text('我的收入'))
            wait_until(Text('本月收入(元)').exists, timeout_secs=20)
            time.sleep(1)
            found = a.find_elements_by_css_selector('.num')[2].text
            click(Text('结算中心'))
            wait_until(Text('结算设置').exists, timeout_secs=20)
            time.sleep(1)
            level = a.find_elements_by_css_selector('.num')[1].text
            print(nick, found, level)
            js = "document.getElementsByClassName('aside-inner')[0].scrollTop=150"
            a.execute_script(js)
            click(Text('等级权益'))
            time.sleep(2)
            wait_until(Text('我的等级').exists)
            le = a.find_element_by_css_selector('.lev-num').text.split('.')[1]
            le = int(le)
            click(Text('信用分'))
            time.sleep(2)
            record = int(a.find_elements_by_css_selector('.green')[0].text[:-1])
            print(nick, record)
            level = int(float(level.replace(',', '').replace('￥', '') if level else 0))
            found = float(found.replace(',', '')) if (found != '-' and found != '0.00') else 0
            pv_last = int(pv_last) if pv_last != '--' else 0

            print(nick, le)
            print(nick, 'level', level, 'found', found, 'pv_last', pv_last, 'found_last', found_last)
            # 总播放量
            x = rq.post('http://121.199.78.122/post_acc_info/',
                        {'level': level, 'record': record, 'le': le, 'uid': uid, 'found': found, 'pv_last': pv_last,
                         'found_last': found_last,
                         'nick': nick,
                         'sy': 1,
                         'acc': acc, 'has_plus': 2,
                         'date_time': datetime.now().strftime('%Y-%m-%d')})
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"账号信息...",
                 "info": {'total_found': level, 'record': record, 'le': le, 'uid': uid, 'found': found, 'pv_last': pv_last,
                          'found_last': found_last,
                          'nick': nick,
                          'total_pv': total_pv,
                          'acc': acc, 'has_plus': 2,
                          'date_time': datetime.now().strftime('%Y-%m-%d')}, "acc": acc})
        except Exception as e:
            traceback.print_exc()
        try:
            kwargs["WORKING_TASK"].remove(acc)
            kwargs["INFO_Q"].put_nowait(
                {"thread_id": int(kwargs["id"]), "process": f"结束...", "acc": acc})
            a.quit()
        except:
            pass
