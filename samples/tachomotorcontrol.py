#!/usr/bin/python

import sys, itertools, time
sys.path.append('/home/robot/src/ev3local')

from ev3local.edutil import gen_events, gen_scaledvalue

def main():

    from ev3local.pyev3 import DutyCycle
    dutycycleA = DutyCycle('outA')
    dutycycleAcr = dutycycleA.setdutycyclesp()

    dutycycleB = DutyCycle('outB')
    dutycycleBcr = dutycycleB.setdutycyclesp()

    try:
        from ev3local.edutil import grepdevice
        devicepath, _ = grepdevice("PLAYSTATION")
        print "Controller found. Input loop started."

        from ev3local.edutil import InputDevice
        device = InputDevice(devicepath)

        import ev3local.edutil
        absinfo1 = ev3local.edutil.absinfo(device, 1)
        absinfo2 = ev3local.edutil.absinfo(device, 5)

        events = gen_events(devicepath, (1, 5))
        values1 = gen_scaledvalue(events, absinfo1.min, absinfo1.max, -75, 75, index=1)
        values2 = gen_scaledvalue(values1, absinfo2.min, absinfo2.max, 75, -75, index=5)

        looptimer = LoopTimer()
        looptimer.init()
        for values in values2:
            value1 = values[1]
            value2 = values[5]
            if value1:
                dutycycleAcr.send(int(value1))
            if value2:
                dutycycleBcr.send(int(value2))
            looptimer.sleep()

    finally:
        dutycycleAcr.close()
        dutycycleBcr.close()


class LoopTimer(object):

    def __init__(self, looptime=1/30.0):
        self.looptime = looptime
        self._time = time.time
        self._sleep = time.sleep

    def init(self):
        self.t0 = self._time()

    def sleep(self):
        dt = self._time() - self.t0
        timetosleep = self.looptime - dt
        if timetosleep<0:
            print "Oops", timetosleep, dt
        else:
            self._sleep(timetosleep)
        self.t0 = self._time()



if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass