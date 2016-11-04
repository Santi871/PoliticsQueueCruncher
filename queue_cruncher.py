import praw
from OAuth2Util import OAuth2Util
from gui import gui_main
from PyQt4 import QtGui, QtCore
import sys
import datetime
from bot_threading import own_thread
import webbrowser
from bs4 import BeautifulSoup
import requests


class GUI(QtGui.QMainWindow, gui_main.Ui_MainWindow):

    def __init__(self, queue_cruncher, parent=None):
        super(GUI, self).__init__(parent)
        self.setupUi(self)
        self.qc = queue_cruncher
        self.current_listed_posts = None
        self.create_populate_reports_list_thread()
        self.pushButton_17.clicked.connect(self.create_populate_reports_list_thread)
        self.tableWidget_2.setColumnCount(4)
        self.statusbar.showMessage("Ready.")
        self.tableWidget_2.itemSelectionChanged.connect(self.select_post)
        self.pushButton_15.clicked.connect(self.open_user_profile)

    def create_populate_reports_list_thread(self):
        self.current_listed_posts = dict()
        self.qc.get_reports(table_widget=self.tableWidget_2, status_bar=self.statusbar, gui_app=self)

    def get_selected_row_data(self):
        item = self.tableWidget_2.selectionModel().selectedRows()[0]
        data = self.tableWidget_2.model().index(item.row(), 3).data()
        return self.current_listed_posts.get(data, None)

    def select_post(self):
        data = self.get_selected_row_data()
        webpage = requests.get(data.url).text
        soup = BeautifulSoup(webpage, "html.parser")
        self.lineEdit_7.setText(soup.title.string)
        self.lineEdit_2.setText(data.title)

    def open_user_profile(self):
        data = self.get_selected_row_data()
        webbrowser.open("https://reddit.com/user/" + data.author.name)


class QueueCruncher:

    def __init__(self):
        self.r = praw.Reddit(user_agent="windows:PoliticsQueueCruncher v0.1 by /u/Santi871")
        self._authenticate()

    def _authenticate(self):
        o = OAuth2Util(self.r)
        o.refresh(force=True)
        self.r.config.api_request_delay = 1

    @own_thread
    def get_reports(self, r, o, table_widget, status_bar, gui_app):
        # status_bar.clearMessage()
        # status_bar.showMessage("Fetching reported posts...")

        reports = r.get_reports('politics', limit=None)
        table_widget.setRowCount(0)
        for n, post in enumerate(reports):
            cur_row = table_widget.rowCount()
            table_widget.insertRow(cur_row)
            timestamp = datetime.datetime.fromtimestamp(post.created).strftime("%Y-%m-%d %H:%M:%S")

            if post.fullname.startswith("t1"):
                post_type = "Comment"
            else:
                post_type = "Submission"

            table_widget.setItem(cur_row, 0, QtGui.QTableWidgetItem(post_type))
            table_widget.setItem(cur_row, 1, QtGui.QTableWidgetItem(post.author.name))
            table_widget.setItem(cur_row, 2, QtGui.QTableWidgetItem(timestamp))
            table_widget.setItem(cur_row, 3, QtGui.QTableWidgetItem(post.id))
            gui_app.current_listed_posts[post.id] = post

        # status_bar.clearMessage()
        # status_bar.showMessage("Ready.")

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
