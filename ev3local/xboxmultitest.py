"""Program to test whether we can recieve xbox events on multiple threats
"""

import sys

from ev3local.xbox import XBoxStateController

name1 = sys.argv[1]
name2 = sys.argv[2]

class XBoxStatePrintController(XBoxStateController):

    def __init__(self, name, *args):
        super(XBoxStatePrintController, self).__init__(*args)
        self._name = name

    def _callback(self, event):
        super(XBoxStatePrintController, self)._callback(event)
        print self._name + "_" + str(event.value)

from ev3local.xbox import *

xevents1 = XCEvents()
xevents2 = XCEvents()

controller1 = XBoxStatePrintController(name1, xevents1)
controller2 = XBoxStatePrintController(name2, xevents2)

xevents1.__enter__()
#xevents2.__enter__()
try:
    while True:
        import time
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    xevents1.__exit__(None, None, None)
    #xevents2.__exit__(None, None, None)



