import praw
from OAuth2Util import OAuth2Util
from gui import gui_main
from PyQt4 import QtGui, QtCore
import sys
import datetime
import webbrowser
from bs4 import BeautifulSoup
from threading import Thread
import time
import requests


def create_reddit():
    r = praw.Reddit(user_agent="windows:PoliticsQueueCruncher v0.2 by /u/Santi871")
    o = OAuth2Util(r)
    r.config.api_request_delay = 1
    o.refresh()
    return r, o


def check_filters(filters, post):
    if not filters:
        return True

    try:
        return any(word.lower() in post.title.lower() for word in filters)
    except AttributeError:
        return any(word.lower() in post.body.lower() for word in filters)


class AlreadyDone(Exception):
    pass


class LiveModqueueFeedThread(QtCore.QThread):
    def __init__(self, filters_line, post_type, check_box):
        QtCore.QThread.__init__(self)
        self.filters_line = filters_line
        self.post_type = post_type
        self.check_box = check_box

    def __del__(self):
        self.wait()

    def run(self):
        r, o = create_reddit()

        starts_with = 't'
        if self.post_type == 1:
            starts_with = 't3'
        elif self.post_type == 2:
            starts_with = 't1'

        while self.check_box.isChecked():
            filters = self.filters_line.text().split(',')
            o.refresh()
            reports = r.get_reports('politics', limit=50, fetch=True)

            for post in reports:
                if post.fullname.startswith(starts_with) and check_filters(filters, post):
                    self.emit(QtCore.SIGNAL('add_feed_post(PyQt_PyObject,PyQt_PyObject)'), post, 0)
            time.sleep(5)


class ModqueueFetcherThread(QtCore.QThread):
    def __init__(self, filters, post_type):
        QtCore.QThread.__init__(self)
        self.filters = filters
        self.post_type = post_type

    def __del__(self):
        self.wait()

    def run(self):
        r, o = create_reddit()

        reports = r.get_reports('politics', limit=None)

        starts_with = 't'
        if self.post_type == 1:
            starts_with = 't3'
        elif self.post_type == 2:
            starts_with = 't1'

        for post in reports:
            if post.fullname.startswith(starts_with) and check_filters(self.filters, post):
                self.emit(QtCore.SIGNAL('add_post(PyQt_PyObject)'), post)
                post.o = o


class GUI(QtGui.QMainWindow, gui_main.Ui_MainWindow):

    def __init__(self,parent=None):
        super(GUI, self).__init__(parent)
        self.setupUi(self)
        self.fetcher_thread = None
        self.feed_thread = None
        self.already_done = list()
        self.current_listed_posts = dict()
        # self.create_populate_reports_list_thread()
        self.pushButton_17.clicked.connect(self.create_populate_reports_list_thread)
        self.tableWidget_2.setColumnCount(4)
        self.statusbar.showMessage("Ready.")
        self.tableWidget_2.itemSelectionChanged.connect(self.select_post)
        self.pushButton_15.clicked.connect(self.open_user_profile)
        self.pushButton_21.clicked.connect(self.open_link)
        self.checkBox.clicked.connect(self.reports_feed)
        self.cur_queue_size = 0

    def create_populate_reports_list_thread(self):
        self.cur_queue_size = 0
        self.label_11.setText("Queue size: 0")
        self.pushButton_17.setText("Refreshing...")
        self.pushButton_17.setEnabled(False)
        self.tableWidget_2.setRowCount(0)
        self.current_listed_posts = dict()
        filters = self.lineEdit.text().split(',')

        post_type = 0
        if self.radioButton_2.isChecked():
            post_type = 2
        if self.radioButton.isChecked():
            post_type = 1

        self.fetcher_thread = ModqueueFetcherThread(filters, post_type)
        self.connect(self.fetcher_thread, QtCore.SIGNAL("add_post(PyQt_PyObject)"), self.add_post)
        self.connect(self.fetcher_thread, QtCore.SIGNAL("finished()"), self.done_fetching_queue)
        self.connect(self.fetcher_thread, QtCore.SIGNAL('update_queue_length(PyQt_PyObject)'), self.update_queue_size)
        self.fetcher_thread.start()

    def update_queue_size(self, num, add_mode=False):
        if add_mode:
            self.cur_queue_size += num
        else:
            self.cur_queue_size = num
        self.label_11.setText("Queue size: " + str(self.cur_queue_size))

    def done_fetching_queue(self):
        self.pushButton_17.setEnabled(True)
        self.pushButton_17.setText("Refresh")

    def reports_feed(self):
        post_type = 0
        if self.radioButton_2.isChecked():
            post_type = 2
        if self.radioButton.isChecked():
            post_type = 1

        self.feed_thread = LiveModqueueFeedThread(self.lineEdit, post_type, self.checkBox)
        self.connect(self.feed_thread, QtCore.SIGNAL("add_feed_post(PyQt_PyObject,PyQt_PyObject)"), self.add_post)
        self.connect(self.feed_thread, QtCore.SIGNAL('update_queue_length(PyQt_PyObject)'), self.update_queue_size)
        self.feed_thread.start()

    def get_selected_row_data(self):
        item = self.tableWidget_2.selectionModel().selectedRows()[0]
        data = self.tableWidget_2.model().index(item.row(), 3).data()
        data = self.current_listed_posts.get(data, None)
        return data

    def add_post(self, post, position=None):
        if post.id in self.already_done:
            return

        if post.author is None:
            return
        if position is None:
            position = self.tableWidget_2.rowCount()

        self.tableWidget_2.insertRow(position)
        timestamp = datetime.datetime.fromtimestamp(post.created).strftime("%Y-%m-%d %H:%M:%S")

        if post.fullname.startswith("t1"):
            post_type = "Comment"
        else:
            post_type = "Submission"

        self.tableWidget_2.setItem(position, 0, QtGui.QTableWidgetItem(post_type))
        self.tableWidget_2.setItem(position, 1, QtGui.QTableWidgetItem(post.author.name))
        self.tableWidget_2.setItem(position, 2, QtGui.QTableWidgetItem(timestamp))
        self.tableWidget_2.setItem(position, 3, QtGui.QTableWidgetItem(post.id))
        self.current_listed_posts[post.id] = post
        self.update_queue_size(1, add_mode=True)
        self.already_done.append(post.id)

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


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    splash_pix = QtGui.QPixmap('splash_loading.png')
    splash = QtGui.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    form = GUI()
    form.show()
    splash.finish(form)
    app.exec_()
