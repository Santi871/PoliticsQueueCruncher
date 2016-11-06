import praw
from OAuth2Util import OAuth2Util
from gui import gui_main
from PyQt4 import QtGui, QtCore
import sys
import datetime
from bot_threading import own_thread
import webbrowser
from bs4 import BeautifulSoup
from threading import Thread
import time
import requests


class GUI(QtGui.QMainWindow, gui_main.Ui_MainWindow):

    def __init__(self, queue_cruncher, parent=None):
        super(GUI, self).__init__(parent)
        self.setupUi(self)
        self.qc = queue_cruncher
        self.qc.gui = self
        self.current_listed_posts = None
        self.create_populate_reports_list_thread()
        self.pushButton_17.clicked.connect(self.create_populate_reports_list_thread)
        self.tableWidget_2.setColumnCount(4)
        self.statusbar.showMessage("Ready.")
        self.tableWidget_2.itemSelectionChanged.connect(self.select_post)
        self.pushButton_15.clicked.connect(self.open_user_profile)
        self.pushButton_21.clicked.connect(self.open_link)
        self.checkBox.clicked.connect(self.reports_feed)

    def create_populate_reports_list_thread(self):
        self.current_listed_posts = dict()
        post_type = 0
        if self.radioButton_2.isChecked():
            post_type = 2
        if self.radioButton.isChecked():
            post_type = 1

        self.qc.get_reports(post_type=post_type)

    def reports_feed(self):
        post_type = 0
        if self.radioButton_2.isChecked():
            post_type = 2
        if self.radioButton.isChecked():
            post_type = 1

        self.qc.update_reports_list(post_type=post_type)

    def get_selected_row_data(self):
        item = self.tableWidget_2.selectionModel().selectedRows()[0]
        data = self.tableWidget_2.model().index(item.row(), 3).data()
        return self.current_listed_posts.get(data, None)

    def select_post(self):
        self.lineEdit_6.clear()
        self.lineEdit_7.clear()

        try:
            data = self.get_selected_row_data()
        except IndexError:
            return

        if isinstance(data, praw.objects.Submission):
            # Submission selected
            self.tabWidget.setTabEnabled(0, True)
            self.tabWidget.setCurrentIndex(0)
            self.tabWidget.setTabEnabled(1, False)
            thread = Thread(target=self.get_article_title, kwargs={'data': data})
            thread.start()
            self.show_webpage(data.url)
            self.lineEdit_6.setText(data.domain)
            self.lineEdit_2.setText(data.title)
        else:
            # Comment selected
            self.tabWidget.setTabEnabled(1, True)
            self.tabWidget.setCurrentIndex(1)
            self.tabWidget.setTabEnabled(0, False)
            self.textEdit.setText(data.body)
            self.lineEdit_9.setText(data.submission.title)
            self.webView_2.load(QtCore.QUrl(data.permalink + "?context=10000"))
            self.webView_2.show()

    def open_link(self):
        data = self.get_selected_row_data()
        webbrowser.open(data.url)

    def open_user_profile(self):
        data = self.get_selected_row_data()
        webbrowser.open("https://reddit.com/user/" + data.author.name)

    def get_article_title(self, data):
        webpage = requests.get(data.url).text
        soup = BeautifulSoup(webpage, "html.parser")
        self.lineEdit_7.setText(soup.title.string)

    def show_webpage(self, url):
        self.webView.load(QtCore.QUrl(url))
        self.webView.show()

    def get_reports_filter(self):
        return self.lineEdit.text().split(',')


class QueueCruncher:

    def __init__(self):
        self.r = praw.Reddit(user_agent="windows:PoliticsQueueCruncher v0.1 by /u/Santi871")
        self._authenticate()
        self.already_done = list()
        self.gui = None

    def _authenticate(self):
        o = OAuth2Util(self.r)
        o.refresh(force=True)
        self.r.config.api_request_delay = 1

    @staticmethod
    def check_filters(filters, post):
        try:
            return any(word.lower() in post.title.lower() for word in filters)
        except AttributeError:
            return any(word.lower() in post.body.lower() for word in filters)

    @own_thread
    def get_reports(self, r, o, post_type):
        self.gui.label_11.setText("Queue size: 0")
        self.gui.pushButton_17.setText("Refreshing...")
        self.gui.pushButton_17.setEnabled(False)
        self.gui.tableWidget_2.setRowCount(0)
        reports = r.get_reports('politics', limit=None)
        filters = self.gui.get_reports_filter()
        queue_num = 0

        starts_with = 't'
        if post_type == 1:
            starts_with = 't3'
        elif post_type == 2:
            starts_with = 't1'

        for post in reports:
            if post.fullname.startswith(starts_with) and self.check_filters(filters, post):
                self.add_post(post)
                self.already_done.append(post.id)
                queue_num += 1
                self.gui.label_11.setText("Queue size: " + str(queue_num))

        self.gui.pushButton_17.setEnabled(True)
        self.gui.pushButton_17.setText("Refresh")

    @own_thread
    def update_reports_list(self, r, o, post_type):
        starts_with = 't'
        if post_type == 1:
            starts_with = 't3'
        elif post_type == 2:
            starts_with = 't1'

        while self.gui.checkBox.isChecked():
            filters = self.gui.get_reports_filter()
            o.refresh()
            reports = r.get_reports('politics', limit=50, fetch=True)

            for post in reports:
                if post.fullname.startswith(starts_with) and post.id not in self.already_done and \
                        self.check_filters(filters, post):
                    self.add_post(post, position=0)
                    self.already_done.append(post.id)
            time.sleep(5)

    def add_post(self, post, position=None):

        if post.author is None:
            return
        if position is None:
            position = self.gui.tableWidget_2.rowCount()

        self.gui.tableWidget_2.insertRow(position)
        timestamp = datetime.datetime.fromtimestamp(post.created).strftime("%Y-%m-%d %H:%M:%S")

        if post.fullname.startswith("t1"):
            post_type = "Comment"
        else:
            post_type = "Submission"

        self.gui.tableWidget_2.setItem(position, 0, QtGui.QTableWidgetItem(post_type))
        self.gui.tableWidget_2.setItem(position, 1, QtGui.QTableWidgetItem(post.author.name))
        self.gui.tableWidget_2.setItem(position, 2, QtGui.QTableWidgetItem(timestamp))
        self.gui.tableWidget_2.setItem(position, 3, QtGui.QTableWidgetItem(post.id))
        self.gui.current_listed_posts[post.id] = post


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    splash_pix = QtGui.QPixmap('splash_loading.png')
    splash = QtGui.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    qc = QueueCruncher()
    form = GUI(queue_cruncher=qc)
    form.show()
    splash.finish(form)
    app.exec_()
