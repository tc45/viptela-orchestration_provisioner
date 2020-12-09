import threading
import datetime


class myThread (threading.Thread):

    def __init__(self, name, counter):
        threading.Thread.__init__(self)
        self.threadID = counter
        self.name = name
        self.counter = counter

    def run(self):
        print("\nStarting " + self.name)
        print_date(self.name, self.counter)
        print("Exiting " + self.name)


def print_date(threadName, counter):
    datefields = []
    today = datetime.date.today()
    datefields.append(today)
    print("{}[{}]: {}".format( threadName, counter, datefields[0] ))