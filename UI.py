import json
import os
import shutil
import sys

import cv2 as cv
import traceback
from multiprocessing import Process, Manager

import requests
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QVariant
from PyQt5.QtGui import QPixmap, QFont, QCursor
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, \
    QStackedWidget, QScrollArea, QMainWindow, QFrame, QTextEdit, QFileDialog, QRadioButton

# ------------------------------ 主窗口 ---------------------------------------------
from helium import start_firefox

from func import Sql, ACC_Q, TASK_Q, mtd_run, disable, INFO_Q, login_acc, task_run

DIR = ''
if getattr(sys, 'frozen', False):
    DIR = os.path.dirname(sys.executable)
elif __file__:
    DIR = os.path.dirname(__file__)

DIR = DIR.replace('\\', '/')
os.chdir(DIR)
os.environ['NO_PROXY'] = '121.199.78.122'


class Mtd(QThread):
    s = pyqtSignal(dict)

    def __init__(self, run_func, run_args, del_func=lambda x, y: 0, del_args={}):
        super(Mtd, self).__init__()
        if del_args is None:
            del_args = {1: 0}
        self.rf = run_func
        self.ra = run_args
        self.df = del_func
        self.da = del_args

    def run(self):
        self.rf(self.s, **self.ra)

    def __del__(self):
        self.df(**self.da)


class Bl(QLabel):
    s = pyqtSignal()
    se = pyqtSignal(str, str, str)

    def __init__(self, t, cls=None):
        super(Bl, self).__init__(t)
        self.setAlignment(Qt.AlignCenter)
        self.kw = cls
        self.setStyleSheet("""
            Bl {
                font-size: 15px;
                color: #fff;
                padding: 5px;
                background-color: #cf0;
            }
            Bl:hover {
                color: #202020;
                padding: 7px;
            }
        """)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == Qt.LeftButton:
            self.s.emit()
            if self.kw:
                self.se.emit(self.kw.acc, self.kw.psd, self.kw.cookies)


class Le(QLineEdit):
    s = pyqtSignal()

    def __init__(self):
        super(Le, self).__init__()
        self.setFont(QFont("黑体"))

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.s.emit()


class Lb(QLabel):
    s = pyqtSignal()

    def __init__(self):
        super(Lb, self).__init__()

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.s.emit()


class Top(QWidget):
    is_press = False
    ox = 0
    oy = 0
    s = pyqtSignal(int, int)
    e = pyqtSignal()

    def __init__(self):
        super(Top, self).__init__()
        self.setFixedSize(960, 45)
        self.icon = QLabel()
        self.icon.setFixedSize(60, 40)
        self.icon.setProperty("name", "icon")
        self.icon.setPixmap(QPixmap(f"{DIR}/icon/sc.png"))
        self.select = QComboBox()
        self.select.setFont(QFont("黑体"))
        self.iqy = Le()
        self.iqy.setReadOnly(True)
        self.iqy.setAlignment(Qt.AlignCenter)
        self.iqy.s.connect(self.select.showPopup)
        self.select.setLineEdit(self.iqy)
        self.select.addItems(["爱奇艺", "使用反馈 -> <Github/FreeHe>", "微信 : Ms744593      -      QQ : 849095347"])
        self.select.setItemData(1, QVariant(0), Qt.UserRole - 1)
        self.select.setItemData(2, QVariant(0), Qt.UserRole - 1)
        self.select.setItemData(1, Qt.lightGray, Qt.BackgroundColorRole)
        self.select.setItemData(2, Qt.lightGray, Qt.BackgroundColorRole)
        self.select.setFixedSize(350, 30)
        self.min = Lb()
        self.close = Lb()
        self.min.setProperty("name", "min")
        self.close.setProperty("name", "close")
        self.min.setFixedSize(30, 30)
        self.close.setFixedSize(30, 30)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.icon)
        self.lay.addStretch()
        self.lay.addWidget(self.select)
        self.lay.addStretch()
        self.lay.addWidget(self.min)
        self.lay.addSpacing(10)
        self.lay.addWidget(self.close)
        self.lay.addSpacing(20)
        self.setLayout(self.lay)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.is_press = True
        self.ox = QCursor.pos().x()
        self.oy = QCursor.pos().y()
        self.e.emit()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self.is_press:
            rx = QCursor.pos().x() - self.ox
            ry = QCursor.pos().y() - self.oy
            self.s.emit(rx, ry)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.is_press = False
        self.ox, self.oy = 0, 0


class Bottom(QWidget):
    def __init__(self):
        super(Bottom, self).__init__()
        self.setFixedSize(960, 45)
        self.lay = QHBoxLayout()
        self.data = Bl("查看数据")
        self.data.s.connect(self.show_data)
        self.Lq = Lb()
        self.Lq.setFixedSize(600, 30)
        self.Lq.setFont(QFont("黑体"))
        self.Lq.setStyleSheet("Lb {color:#aaa}")
        self.S = QLabel()
        self.S.setProperty("name", "S")
        self.S.setFixedSize(10, 10)
        self.lay.addWidget(self.data)
        self.lay.addStretch()
        self.lay.addWidget(self.Lq)
        self.lay.addSpacing(10)
        self.lay.addWidget(self.S)
        self.lay.addStretch()
        self.lay.addSpacing(70)
        self.setLayout(self.lay)

    def show_data(self):
        start_firefox('file:///D:/GitHub/FreeSC/data.html')


# ------------------------------ 爱奇艺 ---------------------------------------------


class AvEdit(QWidget):

    def __init__(self, acc, parent):
        super(AvEdit, self).__init__()
        self.parent = parent
        self.acc = acc
        self.cols = None
        self.setFixedSize(945, 445)
        self.top = QWidget()
        self.top.setFixedSize(945, 30)
        self.top_lay = QHBoxLayout()
        self.top_lay.setContentsMargins(0, 0, 0, 0)
        self.top_back = Bl("返回")
        self.top_back.s.connect(self.back)
        self.top_finish = Bl("完成")
        self.top_finish.setFixedSize(50, 30)
        self.top_finish.s.connect(self.finish)
        self.top_back.setFixedSize(50, 30)
        self.top_lay.addWidget(self.top_back)
        self.top_lay.addStretch()
        self.top_lay.addWidget(self.top_finish)
        self.top_lay.addSpacing(10)
        self.top.setLayout(self.top_lay)
        self.lay = QVBoxLayout()
        self.lay.addWidget(self.top)
        self.Edit = QMainWindow()
        self.Edit.setFixedSize(935, 400)
        self.scroll = QScrollArea()
        self.scroll.setFixedSize(935, 400)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.centre = QWidget()
        self.centre.setFixedWidth(935)
        self.centre.setProperty("name", "ect")
        self.centre_lay = QVBoxLayout()
        self.centre_lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.vits = dict({})
        self.add = Bl("添加视频")
        self.add.setFixedSize(80, 30)
        self.add.s.connect(self.add_vc)
        self.centre_lay.addWidget(self.add)
        self.centre.setLayout(self.centre_lay)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.centre)
        self.Edit.setCentralWidget(self.scroll)
        self.lay.addWidget(self.Edit)
        self.setLayout(self.lay)

    def finish(self):
        EDIT_D[self.acc] = list([])
        for v in self.vits.keys():
            dic = {
                "vpath": v,
                "image": self.vits[v].image,
                "title": self.vits[v].contents_title.toPlainText(),
                "desc": self.vits[v].contents_desc.text(),
                "col": self.vits[v].contents_sel_col.currentText(),
                "cls": self.vits[v].contents_sel_cls.currentText(),
                "org": self.vits[v].original.isChecked(),
                "tags": self.vits[v].tags.toPlainText()
            }
            EDIT_D[self.acc].append(dic)
        self.parent.stack.setCurrentWidget(self.parent.Acc)
        QApplication.processEvents()

    def add_vc(self):
        try:
            if len(self.vits) < 20:
                files, _ = QFileDialog.getOpenFileNames(self, "选取视频", f"{DIR}", "*.mp4;*.avi")
                all_ = [i for i in EDIT_D.values()]
                all_f = list([])
                for f in all_:
                    for a in f:
                        all_f.append(a['vpath'])
                for f in files[:20 - len(self.vits)]:
                    if f not in [i[0] for i in self.vits] and f not in all_f:
                        try:
                            self.vits[f] = Vit(self.acc, self, f)
                        except:
                            continue
                        self.centre_lay.removeWidget(self.add)
                        self.centre_lay.addWidget(self.vits[f])
                        self.centre_lay.addWidget(self.add)
                        self.centre.setFixedHeight(self.centre.height() + 130)
                        self.centre.setLayout(self.centre_lay)
                        QApplication.processEvents()
        except:
            traceback.print_exc()

    def back(self):
        self.parent.stack.setCurrentWidget(self.parent.Acc)

    def init_vs(self):
        for v in self.vits.values():
            self.centre_lay.removeWidget(v)
            v.setParent(None)
        self.centre.setFixedHeight(50)
        self.centre.setLayout(self.centre_lay)
        QApplication.processEvents()
        self.vits = dict({})
        if self.acc in list(EDIT_D.keys()):
            for v in EDIT_D[self.acc]:
                self.centre_lay.removeWidget(self.add)
                self.vits[v["vpath"]] = Vit(self.acc, self, v["vpath"])
                self.vits[v["vpath"]].vpic.setPixmap(QPixmap(v["image"]).scaled(160, 120))
                self.vits[v["vpath"]].contents_title.setText(v["title"])
                self.vits[v["vpath"]].contents_desc.setText(v["desc"])
                self.vits[v["vpath"]].contents_sel_col.setCurrentText(v["col"])
                self.vits[v["vpath"]].contents_sel_cls.setCurrentText(v["cls"])
                self.vits[v["vpath"]].original.setChecked(v["org"])
                self.vits[v["vpath"]].tags.setText(v["tags"])
                self.centre_lay.addWidget(self.vits[v["vpath"]])
                self.centre_lay.addWidget(self.add)
                self.centre.setFixedHeight(self.centre.height() + 130)
            self.centre.setLayout(self.centre_lay)
            QApplication.processEvents()


class Vit(QFrame):

    def __init__(self, acc, parent, mp4):
        super(Vit, self).__init__()
        self.parent = parent
        self.acc = acc
        self.mp4 = mp4
        self.image = ""
        self.setFont(QFont("黑体"))
        self.setFixedSize(750, 120)
        self.setProperty("name", "vit")
        self.setStyleSheet("""
            Vit {
                background-color: #181818;
                padding: 0;
            }
            Lb {
                background-color: #181818;
            }
            QComboBox {
                background-color: #101010;
            }
            QComboBox QAbstractItemView {
                background-color: #181818;
                color: #fff;
                selection-color: #cccccc;
            }
            QLabel,QTextEdit {
                background-color: #101010;
                border: 0 solid #fff;
                color: #fff;
            }
            QLineEdit[name="cd"] {
                color: #aaa;
            }
            QLineEdit {
                background-color: #181818;
                border: 0 solid #fff;
                color: #fff;
            }
            QTextEdit[name="cte"] {
                font-size: 15px;
                background-color: #181818;
            }
            QRadioButton {
                font-size: 15px;
                color: #606060;
            }
        """)
        self.vpic = Lb()
        self.tgs = ["游戏", "搞笑", "原创", "电影", "电视剧", "数码", "体育", "音乐"]
        self.vpic.setFixedSize(160, 120)
        self.vpic.s.connect(self.change_im)
        self.lay = QHBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.contents = QWidget()
        self.contents.setFixedSize(400, 100)
        self.contents.setProperty("name", "cnt")
        self.contents_lay = QVBoxLayout()
        self.contents_lay.setContentsMargins(0, 0, 0, 0)
        title = self.mp4.split(os.path.dirname(self.mp4))[-1][1:-4]
        self.contents_title = QTextEdit()
        self.contents_title.setFixedSize(400, 40)
        self.contents_title.setProperty("name", "cte")
        self.contents_title.setPlaceholderText("标题 : 不超过30字")
        self.contents_title.setText(title[:30])
        self.contents_desc = QLineEdit()
        self.contents_desc.setFixedSize(400, 20)
        self.contents_desc.setPlaceholderText("一句话推荐 : 简介")
        self.contents_desc.setProperty("name", "cd")
        self.contents_desc.setText(title)
        self.contents_title.setFont(QFont("黑体"))
        self.contents_desc.setFont(QFont("黑体"))
        self.contents_sel = QWidget()
        self.contents_sel.setFixedSize(400, 40)
        self.contents_sel_lay = QHBoxLayout()
        self.contents_sel_lay.setContentsMargins(0, 0, 0, 0)
        self.contents_sel_col = QComboBox()
        self.contents_sel_col.setFont(QFont("黑体"))
        self.col = Le()
        self.col.setReadOnly(True)
        self.col.setAlignment(Qt.AlignLeft)
        self.col.s.connect(self.contents_sel_col.showPopup)
        self.contents_sel_col.setLineEdit(self.col)
        self.its = self.parent.cols.split(';') if self.parent.cols else []
        self.its = [[k.split("><")[0], k.split("><")[1]] for k in self.its if k.split("><")[2] == "已发布"]
        self.contents_sel_col.addItems(["单个视频", *[t[0] for t in self.its]])
        self.contents_sel_col.setFixedSize(150, 25)
        self.contents_sel_col.currentTextChanged.connect(self.dis_cls)
        self.contents_sel_cls = QComboBox()
        self.contents_sel_cls.setFont(QFont("黑体"))
        self.cls = Le()
        self.cls.setReadOnly(True)
        self.cls.setAlignment(Qt.AlignLeft)
        self.cls.s.connect(self.contents_sel_cls.showPopup)
        self.contents_sel_cls.setLineEdit(self.cls)
        self.contents_sel_cls.setFixedSize(100, 25)
        self.contents_sel_cls.addItems(self.tgs)
        self.original = QRadioButton('原创')
        self.original.setChecked(True)
        self.original.setFont(QFont("黑体"))
        self.contents_sel_lay.addWidget(self.contents_sel_col)
        self.contents_sel_lay.addWidget(self.contents_sel_cls)
        self.contents_sel_lay.addStretch()
        self.contents_sel_lay.addWidget(self.original)
        self.contents_sel_lay.addSpacing(10)
        self.contents_sel.setLayout(self.contents_sel_lay)
        self.contents_lay.addWidget(self.contents_title)
        self.contents_lay.addWidget(self.contents_desc)
        self.contents_lay.addWidget(self.contents_sel)
        self.contents.setLayout(self.contents_lay)
        self.tags = QTextEdit()
        self.tags.setFixedSize(150, 100)
        self.tags.setPlaceholderText("标签 : 以空格和换行分隔")
        self.tags.setFont(QFont('黑体'))
        self.d = Bl("D")
        self.d.setFixedSize(30, 120)
        self.d.setStyleSheet("Bl {background-color: #101010;}")
        self.lay.addWidget(self.vpic)
        self.lay.addWidget(self.contents)
        self.lay.addWidget(self.tags)
        self.lay.addStretch()
        self.lay.addWidget(self.d)
        self.setLayout(self.lay)
        self.d.s.connect(self.delete)
        self.get_img()

    def dis_cls(self):
        if self.contents_sel_col.currentText() != "单个视频":
            for ind, i in enumerate(self.its):
                if i[0] == self.contents_sel_col.currentText() and i[1] in self.tgs:
                    self.contents_sel_cls.setCurrentText(i[1])
                    self.contents_sel_cls.setEnabled(False)
        else:
            self.contents_sel_cls.setEnabled(True)
        QApplication.processEvents()

    def delete(self):
        self.parent.lay.removeWidget(self)
        self.setParent(None)
        del self.parent.vits[self.mp4]

    def get_img(self):
        try:
            f = cv.VideoCapture(self.mp4)
            ret, frame = f.read()
            n = 0
            while ret and n != 20:
                ret, frame = f.read()
                n += 1
            if not os.path.isdir(f"./tmp/{self.acc}"):
                os.mkdir(f"./tmp/{self.acc}")
            im = cv.resize(frame, (1920, 1080), interpolation=cv.INTER_CUBIC)
            cv.imencode(".png", im)[1].tofile(f"./tmp/{self.acc}/{self.contents_title.toPlainText()}.png")
            f.release()
            self.vpic.setPixmap(QPixmap(f"./tmp/{self.acc}/{self.contents_title.toPlainText()}.png").scaled(160, 120))
            self.image = f"./tmp/{self.acc}/{self.contents_title.toPlainText()}.png"
        except:
            traceback.print_exc()

    def change_im(self):
        try:
            im, _ = QFileDialog.getOpenFileName(self, "选择封面", "./", "*.png;*.jpg")
            if im.endswith('png') or im.endswith('jpg'):
                ic = cv.imread(im)
                if ic.shape[0] > 720 and ic.shape[1] > 1080:
                    self.image = im
                    self.vpic.setPixmap(QPixmap(self.image).scaled(160, 120))
        except:
            traceback.print_exc()


class Aaw(QWidget):

    def __init__(self):
        super(Aaw, self).__init__()
        self.setFixedSize(250, 120)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        self.lay = QVBoxLayout()
        self.acc = QLineEdit()
        self.psd = QLineEdit()
        self.acc.setFont(QFont("Ink Free"))
        self.psd.setFont(QFont("Ink Free"))
        self.acc.setFixedSize(230, 25)
        self.acc.setPlaceholderText("请输入账号")
        self.psd.setPlaceholderText("请输入密码")
        self.psd.setFixedSize(230, 25)
        self.b_lay = QHBoxLayout()
        self.b_cancel = Bl("取消")
        self.b_confirm = Bl("确认")
        self.b_cancel.setFixedSize(50, 25)
        self.b_confirm.setFixedSize(50, 25)
        self.b_lay.addWidget(self.b_cancel)
        self.b_lay.addStretch()
        self.b_lay.addWidget(self.b_confirm)
        self.lay.addWidget(self.acc)
        self.lay.addWidget(self.psd)
        self.lay.addLayout(self.b_lay)
        self.setLayout(self.lay)
        self.setStyleSheet("""
            Aaw {
                background-color: #202020;
            }
            QLineEdit {
                background-color: #181818;
                border: 0 solid #fff;
                color: #cf0;
            }
        """)


class Acc(QMainWindow):

    def __init__(self, parent):
        super(Acc, self).__init__()
        self.setFixedSize(945, 445)
        self.parent = parent
        self.scroll = QScrollArea()
        self.scroll.setFixedSize(945, 445)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.centre = QWidget()
        self.centre.setFixedWidth(945)
        self.centre.setProperty("name", "ct")
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lay = QVBoxLayout()
        self.lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.add = Bl("添加账号")
        self.add.setFixedSize(80, 30)
        self.add.s.connect(self.add_ac)
        self.lay.addWidget(self.add)
        self.aits = dict({})  # "acc": Ait, 存储账号列表
        self.add_acc_wg = Aaw()
        self.add_acc_wg.b_cancel.s.connect(lambda: sc.setEnabled(True))
        self.add_acc_wg.b_cancel.s.connect(self.add_acc_wg.hide)
        self.add_acc_wg.b_confirm.s.connect(self.add_ait)
        self.centre.setLayout(self.lay)
        self.scroll.setWidget(self.centre)
        self.setCentralWidget(self.scroll)
        self.acc_p1 = Process(target=mtd_run,
                              args=({'WORKING_TASK': WORKING_TASK, 'ACC_Q': ACC_Q, "INFO_Q": INFO_Q, "id": "1"},), )
        self.acc_p1.daemon = True
        self.acc_p1.start()
        self.acc_p2 = Process(target=mtd_run,
                              args=({'WORKING_TASK': WORKING_TASK, 'ACC_Q': ACC_Q, "INFO_Q": INFO_Q, "id": "2"},), )
        self.acc_p2.daemon = True
        self.acc_p2.start()
        self.acc_p3 = Process(target=mtd_run,
                              args=({'WORKING_TASK': WORKING_TASK, 'ACC_Q': ACC_Q, "INFO_Q": INFO_Q, "id": "3"},), )
        self.acc_p3.daemon = True
        self.acc_p3.start()
        self.init_ait()

    def ait_show(self, x):
        self.aits[x["acc"]].info_nick.setText(x["nick"])
        QApplication.processEvents()
        self.aits[x["acc"]].info_uid.setText("UID : " + x["uid"])
        QApplication.processEvents()
        self.aits[x["acc"]].icon.setPixmap(QPixmap(x["icon"]).scaled(100, 100))
        QApplication.processEvents()
        self.aits[x["acc"]].info_some_lv.setText("Lv" + x["lv"])
        QApplication.processEvents()
        self.aits[x["acc"]].info_some_plus.setText("有专辑" if x["plus"] else "")
        QApplication.processEvents()
        if not x['plus']:
            self.aits[x["acc"]].info_some_plus.hide()
            QApplication.processEvents()
        self.aits[x["acc"]].info_some_record.setText("信用分 " + x["record"])
        QApplication.processEvents()

    # 添加账号
    def add_ac(self):
        self.add_acc_wg.acc.setText("")
        self.add_acc_wg.psd.setText("")
        try:
            self.add_acc_wg.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.add_acc_wg.show()
            disable(sc)
            QApplication.processEvents()
        except:
            traceback.print_exc()

    def init_ait(self):
        while True:
            if SQL.init_ret is not None:
                for i in SQL.init_ret:
                    self.lay.removeWidget(self.add)
                    self.aits[i[0]] = Ait(i[0], i[1], self, i[8], i[9])
                    self.aits[i[0]].s.connect(self.del_ait)
                    self.lay.addWidget(self.aits[i[0]])
                    self.lay.addWidget(self.add)
                    self.centre.setFixedHeight(self.centre.height() + 130)
                    x = {"acc": i[0], "psd": i[1], "lv": i[2], "uid": i[3], "record": i[4], "plus": i[5], "icon": i[6],
                         "nick": i[7], "cols": i[8]}
                    self.ait_show(x)
                    QApplication.processEvents()
                break

    def add_ait(self):
        acc = self.add_acc_wg.acc.text()
        psd = self.add_acc_wg.psd.text()
        if acc in (self.aits.keys()):
            self.add_acc_wg.hide()
            sc.setEnabled(True)
            return
        if acc and psd:
            self.lay.removeWidget(self.add)
            self.aits[acc] = Ait(acc, psd, self, "", "")
            self.aits[acc].s.connect(self.del_ait)
            self.lay.addWidget(self.aits[acc])
            self.lay.addWidget(self.add)
            self.centre.setFixedHeight(self.centre.height() + 130)
            ACC_Q.put_nowait({"acc": f"{acc}", "psd": f"{psd}"})
            self.add_acc_wg.hide()
            sc.setEnabled(True)

    def del_ait(self, acc):
        self.aits[acc].close()
        del self.aits[acc]
        if acc in list(EDIT_D.keys()):
            del EDIT_D[acc]
        SQL.add_sql(f"DELETE FROM ACC WHERE ACC='{acc}';")


class Ait(QLabel):
    s = pyqtSignal(str)

    def __init__(self, acc, psd, parent, cols, cookies):
        super(Ait, self).__init__()
        self.parent = parent
        self.acc = acc
        self.cookies = cookies
        self.psd = psd
        self.cols = cols
        self.setFixedSize(750, 120)
        self.lay = QHBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.icon = QLabel()
        self.icon.setFixedSize(100, 100)
        self.icon.setProperty("name", "icon")
        self.info = QWidget()
        self.info.setFixedSize(250, 120)
        self.info.setProperty("name", "info")
        self.info_lay = QVBoxLayout()
        self.info_nick = QLabel()
        self.info_nick.setFixedSize(220, 30)
        self.info_nick.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.info_nick.setProperty("name", "nick")
        self.info_nick.setFont(QFont("黑体"))
        self.info_uid = QLabel()
        self.info_uid.setFixedSize(180, 22)
        self.info_uid.setFont(QFont("Ink Free"))
        self.info_uid.setProperty("name", "uid")
        self.info_uid.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.info_some = QWidget()
        self.info_some.setFixedSize(220, 40)
        self.info_some.setProperty("name", "some")
        self.info_some_lay = QHBoxLayout()
        self.info_some_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_some_lay.setContentsMargins(0, 0, 0, 0)
        self.info_some_lv = QLabel()
        self.info_some_lv.setFixedSize(30, 20)
        self.info_some_lv.setProperty("name", "lv")
        self.info_some_lv.setFont(QFont("Ink Free"))
        self.info_some_lv.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.info_some_record = QLabel()
        self.info_some_record.setFixedSize(70, 20)
        self.info_some_record.setProperty("name", "record")
        self.info_some_record.setFont(QFont("Ink Free"))
        self.info_some_record.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.info_some_plus = QLabel()
        self.info_some_plus.setFixedSize(40, 20)
        self.info_some_plus.setProperty("name", "plus")
        self.info_some_plus.setFont(QFont("Ink Free"))
        self.info_some_plus.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.info_some_lay.addWidget(self.info_some_lv)
        self.info_some_lay.addWidget(self.info_some_record)
        self.info_some_lay.addWidget(self.info_some_plus)
        self.info_some.setLayout(self.info_some_lay)
        self.info_lay.addWidget(self.info_nick)
        self.info_lay.addSpacing(5)
        self.info_lay.addWidget(self.info_uid)
        self.info_lay.addWidget(self.info_some)
        self.info.setLayout(self.info_lay)
        self.process = QWidget()
        self.process.setFixedSize(335, 120)
        self.process.setProperty("name", "process")
        self.process_lay = QVBoxLayout()
        self.process_lay.setContentsMargins(0, 0, 0, 0)
        self.process_line = QLabel()
        self.process_line.setProperty("name", "line")
        self.process_line.setFixedSize(270, 40)
        self.process_line.setFont(QFont("黑体"))
        self.process_num = QLabel("0")
        self.process_num.setProperty("name", "num")
        self.process_num.setFixedSize(60, 60)
        self.process_num.setFont(QFont("Ink Free"))
        self.process_add = Bl("添加队列")
        self.process_add.setProperty("name", "add")
        self.process_add.setFixedSize(100, 30)
        self.process_add.s.connect(lambda: self.add_task({'process': ''}))
        self.process_edit = Bl("编辑发布")
        self.process_edit.setProperty("name", "edit")
        self.process_edit.setFixedSize(100, 30)
        self.process_edit.s.connect(lambda: self.parent.parent.init_av(self.acc, self.psd, self.cols))
        self.process_lay_bottom = QHBoxLayout()
        self.process_lay_bottom.setContentsMargins(0, 0, 0, 0)
        self.process_lay_bottom.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.process_lay_bottom.addWidget(self.process_num)
        self.process_lay_bottom.addWidget(self.process_add)
        self.process_lay_bottom.addWidget(self.process_edit)
        self.process_lay.addWidget(self.process_line)
        self.process_lay.addLayout(self.process_lay_bottom)
        self.process.setLayout(self.process_lay)
        self.aside = QWidget()
        self.aside.setFixedSize(45, 120)
        self.aside.setProperty("name", "aside")
        self.aside_lay = QVBoxLayout()
        self.aside_lay.setContentsMargins(0, 0, 0, 0)
        self.aside_lay.setAlignment(Qt.AlignCenter | Qt.AlignHCenter)
        self.aside_login = Bl("H", self)
        self.aside_login.setFixedSize(30, 30)
        self.aside_login.setProperty("name", "aside_login")
        self.aside_login.se.connect(login_acc)
        self.aside_del = Bl("D")
        self.aside_del.setFixedSize(30, 30)
        self.aside_del.setProperty("name", "aside_del")
        self.aside_del.s.connect(self.ait_del)
        self.aside_notice = QLabel()
        self.aside_notice.setFixedSize(30, 30)
        self.aside_notice.setProperty("name", "aside_notice")
        self.aside_lay.addWidget(self.aside_login)
        self.aside_lay.addWidget(self.aside_del)
        self.aside_lay.addWidget(self.aside_notice)
        self.aside.setLayout(self.aside_lay)
        self.lay.setContentsMargins(10, 0, 0, 0)
        self.lay.addWidget(self.icon)
        self.lay.addWidget(self.info)
        self.lay.addWidget(self.process)
        self.lay.addWidget(self.aside)
        self.setLayout(self.lay)
        self.setStyleSheet("""
            QLabel[name="lv"], QLabel[name="record"], QLabel[name="plus"] {
                background-color: #cf0;
                color: #fff;
            }
        """)

    def ait_del(self):
        self.s.emit(self.acc)

    def add_task(self, x):
        try:
            if self.process_add.text() == "取消队列":
                if EDIT_D[self.acc] or "验证失败" in x['process']:
                    QUIT_L.append(self.acc)
                    print('添加取消队列 - ', self.acc)
                self.process_edit.setEnabled(True)
                self.process_add.setText('添加队列')
                self.process.setStyleSheet("background-color:#181818;")
                self.process_edit.show()
                QApplication.processEvents()
            elif self.acc in list(EDIT_D.keys()) and EDIT_D[self.acc] and self.process_add.text() == "添加队列":
                TASK_Q.put_nowait([self.acc, self.psd, EDIT_D[self.acc], self.cookies])
                self.process_add.setText('取消队列')
                self.process.setStyleSheet("background-color:#101010;")
                self.process_edit.hide()
                self.process_edit.setEnabled(False)
                QApplication.processEvents()
        except:
            traceback.print_exc()


# ------------------------------ 腾讯视频 ---------------------------------------------


# ------------------------------ 优酷视频 ---------------------------------------------


# ------------------------------ 哔哩哔哩 ---------------------------------------------


class SC(QWidget):
    ox = 0
    oy = 0

    def init_av(self, acc, psd, cols):
        self.Av.acc = acc
        self.Av.cols = cols
        self.Av.init_vs()
        self.stack.setCurrentWidget(self.Av)

    def __init__(self):
        super(SC, self).__init__()
        global EDIT_D
        try:
            with open("./edit_d.json", "r") as f:
                EDIT_D = json.load(f)
                for k in EDIT_D:
                    tmp = []
                    for v in EDIT_D[k]:
                        if os.path.exists(v['vpath']):
                            tmp.append(v)
                    EDIT_D[k] = tmp
            if not EDIT_D:
                for i in os.listdir("./tmp"):
                    shutil.rmtree(f"./tmp/{i}")
        except:
            traceback.print_exc()
        self.setFixedSize(980, 560)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        self.Top = Top()
        self.Top.s.connect(self.move_xy)
        self.Top.e.connect(self.set_xy)
        self.Top.min.s.connect(self.showMinimized)
        self.Bot = Bottom()
        self.stack = QStackedWidget()
        self.Acc = Acc(self)
        self.Av = AvEdit("", self)
        self.stack.addWidget(self.Acc)
        self.stack.addWidget(self.Av)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.Top)
        self.layout.addWidget(self.stack)
        self.layout.addWidget(self.Bot)
        self.setLayout(self.layout)
        self.task_clock = QTimer()
        self.task_clock.timeout.connect(self.clock)
        self.task_clock.setInterval(1000)
        self.task_clock.start()
        self.clock_count = 0
        self.setStyleSheet("""
            QWidget[name="vit"] {
                background-color: #181818;
                padding: 0;
            }
            SC {
                background-color: #202020;
            }
            Ait, Vit {
                background-color: #181818;
                padding: 0;
            }
            QLabel[name="min"] {
                background-color: #cf0;
                border-radius: 15px;
            }
            QLabel[name="close"] {
                background-color: red;
                border-radius: 15px;
            }
            QComboBox {
                background-color: #3f4046;
                color: #959699;
                border: 0 solid #3f4046;
                font-size: 15px;
            }
            QComboBox QAbstractItemView {
                background-color: #3f4046;
                color: #959699;
                border: 0 solid #3f4046;
            }
            QComboBox QAbstractItemView {
                background-color: #3f4046;
                color: #959699;
                selection-color: #cccccc;
            }
            QComboBox:hover {
                color: #cccccc;
            }
            QComboBox:drop-down {
                border: 0 solid #3f4046;
            }
            Bottom {
                background-color: #cccccc;
            }
            Bl {
                font-size: 15px;
                color: #fff;
                padding: 5px;
                background-color: #cf0;
            }
            Bl:hover {
                color: #202020;
                padding: 7px;
            }
            Bl[name="tn"], Bl[name="task"] {
                background-color: #202020;
                font-size: 17px;
                color: #cf0;
            }
            QLabel[name="S"] {
                border-radius: 5px;
                background-color: #cf0;
            }
            QScrollArea, Acc, QMainWindow, QWidget[name="ct"], QWidget[name="ect"] {
                background-color: #202020;
                border: 0px solid #202020;
                border-color: #202020;
            }
            QScrollArea QScrollBar:vertical {
                max-width: 10;
                border-radius:5px;
                background-color: #cf0;
                border-width: 0px;
            }
            QScrollArea QScrollBar::add-page:vertical {
                background-color: #202020;
            }
            QScrollArea QScrollBar::sub-page:vertical {
                background-color: #202020;
            }
            QScrollArea QScrollBar::add-line:vertical {
                background-color: #202020;
            }
            QScrollArea QScrollBar::sub-line:vertical {
                background-color: #202020;
            }
            QScrollArea QScrollBar::handle:vertical {
                background-color: #37393f;
            }
            QScrollArea QScrollBar::handle:horizontal {
                max-height: 0px;
                max-width: 0px;
            }
            QWidget[name="info"] {
                
            }
            QWidget[name="process"] {
                background-color: #181818;
            }
            QWidget[name="aside"] {
                background-color: #181818;
            }
            QLabel[name="aside_del"], QLabel[name="aside_notice"], QLabel[name="aside_login"], QLabel[name="uid"], QLabel[name="lv"], QLabel[name="record"], QLabel[name="plus"] {
                background-color: #3f4046;
                color: #aaa;
            }
            QLabel[name="nick"], QLabel[name="uid"] {
                background-color: #181818;
                color: #fff;
            }
            QLabel[name="num"], QLabel[name="line"] {
                background-color: #181818;
                color: #fff;
            }
            QLabel[name="num"] {
                font-size: 50px;
            }
            QLabel[name="nick"] {
                font-size: 20px;
            }
            QLabel[name="uid"] {
                background-color: #181818;
                color: #fff;
            }
        """)
        self.info_thread = Mtd(self.mtd_s, run_args={})
        self.info_thread.start()
        self.task_p1 = Process(target=task_run,
                               args=(
                                   {'WORKING_TASK': WORKING_TASK, 'TASK_Q': TASK_Q, "INFO_Q": INFO_Q, "QUIT_L": QUIT_L,
                                    "id": "4"},), )
        self.task_p1.daemon = True
        self.task_p1.start()
        self.task_p2 = Process(target=task_run,
                               args=(
                                   {'WORKING_TASK': WORKING_TASK, 'TASK_Q': TASK_Q, "INFO_Q": INFO_Q, "QUIT_L": QUIT_L,
                                    "id": "5"},), )
        self.task_p2.daemon = True
        self.task_p2.start()

    def clock(self):
        try:
            for t in WORKING_TASK:
                if self.clock_count:
                    self.Bot.S.setStyleSheet("""
                        background-color: #cf0;
                    """)
                    QApplication.processEvents()
                    self.Acc.aits[t].aside_notice.setStyleSheet("""
                        background-color: #cf0;
                    """)
                    QApplication.processEvents()
                else:
                    self.Bot.S.setStyleSheet("""
                        background-color: #202020;
                    """)
                    QApplication.processEvents()
                    self.Acc.aits[t].aside_notice.setStyleSheet("""
                        background-color: #3f4046;
                    """)
                    QApplication.processEvents()
            for t in self.Acc.aits.keys():
                if t not in WORKING_TASK:
                    self.Acc.aits[t].aside_notice.setStyleSheet("""
                        background-color: #3f4046;
                    """)
                QApplication.processEvents()
            for a in EDIT_D:
                n = len(EDIT_D[a])
                if a not in self.Acc.aits.keys():
                    del EDIT_D[a]
                else:
                    self.Acc.aits[a].process_num.setText(str(n))
                    tmp = dict({})
                    for k in EDIT_D:
                        if EDIT_D[k]:
                            tmp[k] = EDIT_D[k]
                    with open("./edit_d.json", "w") as f:
                        json.dump(tmp, f)
            QApplication.processEvents()
        except:
            traceback.print_exc()
        self.clock_count = 0 if self.clock_count == 1 else 1

    def set_xy(self):
        self.ox = self.x()
        self.oy = self.y()

    def move_xy(self, rx, ry):
        self.move(rx + self.ox, ry + self.oy)

    def mtd_s(self, s, **kwargs):
        try:
            while x := INFO_Q.get(block=True):
                if 'vpath' in x.keys():
                    EDIT_D[x['acc']] = [i for i in EDIT_D[x['acc']] if i['vpath'] != x['vpath']]
                if (x['acc'] in list(EDIT_D.keys()) and not EDIT_D[x['acc']] and self.Acc.aits[
                    x['acc']].process_add.text() == "取消队列") or "验证失败" in x["process"]:
                    self.Acc.aits[x['acc']].add_task(x)
                    QApplication.processEvents()
                if "process" in x.keys():
                    try:
                        self.Acc.aits[x["acc"]].process_line.setText(x["process"])
                        self.Bot.Lq.setText(f"账号:{x['acc']} - {x['process']}")
                        QApplication.processEvents()
                    except:
                        traceback.print_exc()
                if "icon" in x.keys():
                    try:
                        self.Acc.ait_show(x)
                        SQL.add_sql(
                            f"INSERT INTO ACC VALUES ('{x['acc']}', '{x['psd']}', '{x['lv']}', '{x['uid']}', '{x['record']}', '{x['plus']}', '{x['icon']}', '{x['nick']}', '{x['cols']}', '{x['cookies']}');"
                        )
                        self.Bot.Lq.setText(f"账号数据:{x['nick']} - 写入数据库")
                        QApplication.processEvents()
                        self.Acc.aits[x['acc']].cols = x['cols']
                        QApplication.processEvents()
                        self.Acc.aits[x['acc']].cookies = x['cookies']
                        QApplication.processEvents()
                    except:
                        traceback.print_exc()
                if "收集合集" in x["process"]:
                    SQL.add_sql(
                        f"UPDATE ACC SET cols=\'{x['cols']}\' WHERE acc=\'{x['acc']}\';"
                    )
                if "cookies" in x.keys():
                    x['cookies'] = x['cookies']
                    SQL.add_sql(
                        f"UPDATE ACC SET cookies=\'{x['cookies']}\' WHERE acc=\'{x['acc']}\';"
                    )
                if "info" in x.keys():
                    SQL.add_sql(
                        f"UPDATE ACC SET level=\'{str(x['info']['le'])}\', nick=\'{str(x['info']['nick'])}\', record=\'{str(x['info']['record'])}\' WHERE acc=\'{x['info']['acc']}\'"
                    )
                    SQL.add_sql(
                        f"INSERT INTO DALIY VALUES (\'{x['info']['acc']}\', \'{x['info']['total_found']}\', \'{x['info']['found']}\', \'{x['info']['found_last']}\', \'{x['info']['total_pv']}\', \'{x['info']['pv_last']}\', \'{x['info']['date_time']}\')"
                    )
        except:
            traceback.print_exc()


def _del():
    tmp = dict({})
    for k in EDIT_D:
        if EDIT_D[k]:
            tmp[k] = EDIT_D[k]
    with open("./edit_d.json", "w") as f:
        json.dump(tmp, f)
    try:
        sc.task_p1.terminate()
    except:
        pass
    try:
        sc.task_p2.terminate()
    except:
        pass
    try:
        os.system("taskkill /F /IM Firefox.exe")
    except:
        pass


if __name__ == "__main__":
    sc = "sc"
    if requests.post('http://121.199.78.122/sc/', {'sc': sc}).text == 'yes':
        WORKING_TASK = Manager().list()
        EDIT_D = dict({})  # acc: [vt...]
        QUIT_L = Manager().list()
        if not os.path.isdir(f"{DIR}/tmp"):
            os.mkdir(f"{DIR}/tmp")
        for i in os.listdir(f"{DIR}"):
            if i.endswith(".png"):
                os.remove(f"{DIR}/{i}")
        try:
            app = QApplication(sys.argv)
            SQL = Sql()
            SQL.add_sql("SELECT * FROM ACC;")
            sc = SC()
            sc.Top.close.s.connect(_del)
            sc.Top.close.s.connect(sc.task_clock.deleteLater)
            sc.Top.close.s.connect(lambda: sys.exit())
            sc.show()
            sys.exit(app.exec_())
        except:
            traceback.print_exc()
