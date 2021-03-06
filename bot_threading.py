import threading
import traceback
from time import sleep
import requests.exceptions
import praw
import OAuth2Util
from retrying import retry


class CreateThread(threading.Thread):
    def __init__(self, thread_id, name, obj, method, kwargs=None):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.obj = obj
        self.method = method
        self.kwargs = kwargs

    def run(self):
        # This loop will run when the thread raises an exception
        while True:
            try:
                methodToRun = self.method(self.obj, **self.kwargs)
                break
            except AssertionError:
                print("------------\nRan into an assertion error\nTrying again\n------------")
                sleep(1)
                print(traceback.format_exc())
                continue
            except (requests.exceptions.HTTPError, praw.errors.HTTPException):
                sleep(2)
                continue
            except requests.exceptions.ConnectionError:
                print("Ran into a ConnectionError")
                sleep(10)
                continue
            except:
                print("*Unhandled exception"
                      " in thread* '%s'." % self.name)
                print(traceback.format_exc())
                sleep(10)


@retry(stop_max_attempt_number=4)
def own_thread(func):
    def wrapped_f(*args, **kwargs):
        # Create a thread with the method we called
        if not kwargs:
            kwargs = None
        bot_obj = args[0]

        r = praw.Reddit(user_agent="windows:PoliticsQueueCruncher v0.2 by /u/Santi871")
        o = OAuth2Util.OAuth2Util(r, configfile='praw.ini')
        r.config.api_request_delay = 1

        if kwargs is not None:
            kwargs['r'] = r
            kwargs['o'] = o
        else:
            kwargs = {'r': r, 'o': o}

        o.refresh()
        thread = CreateThread(1, str(func) + " thread", args[0], func, kwargs)
        thread.start()

    return wrapped_f


