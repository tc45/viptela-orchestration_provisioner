import threading
import datetime
from utils import ping_host
import telnetlib


class myThread (threading.Thread):

    def __init__(self, name, counter, target=None):
        threading.Thread.__init__(self)
        self.threadID = counter
        self.name = name
        self.counter = counter
        self.target = target

    def run(self):
        print("\nStarting " + self.name)
        print_date(self.name, self.counter)
        counter(self.name, self.counter)
        print("Exiting " + self.name)


def counter(threadName, counter):
    import time

    x = 0
    while x < 5:
        datefields = []
        today = datetime.date.today()
        datefields.append(today)
        print("{}[{}]: {} - {}".format( threadName, counter, datefields[0], x))
        time.sleep(2)
        x += 1


def print_date(threadName, counter):
    datefields = []
    today = datetime.date.today()
    datefields.append(today)
    print("{}[{}]: {}".format( threadName, counter, datefields[0] ))