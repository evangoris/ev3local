#!/usr/bin/python

import sys, itertools, time
sys.path.append('/home/robot/src/ev3local')

from ev3local.edutil import gen_events

def main():

    from ev3local.edutil import grepdevice
    devicepath, _ = grepdevice("PLAYSTATION")
    print "Controller found. Input loop started."

    from ev3local.edutil import InputDevice
    device = InputDevice(devicepath)
    codes = (0, 1, 5)
    events = gen_events(devicepath, codes)

    codes_ports = zip(codes, ['outA', 'outB', 'outC'])
    branches = [ (code, try_createbranch(bounds(device, code), port)) for code, port in codes_ports]
    active_branches = [ (code, branch) for code, branch in branches if branch]

    from ev3local.generator import split
    root = split(*unzip(active_branches))

    looptimer = LoopTimer()
    looptimer.init()
    for values in events:
        root.send(values)
        looptimer.sleep()

    root.close()


def try_createbranch(inbounds, port):
    from ev3local.generator import scale, sequence
    from ev3local.edutil import getvalue
    try:
        return sequence([getvalue, scale(inbounds, (75, -75)), cr_dutycycle(port)])
    except IOError:
        # Nothing attached to `port`
        return None


def unzip(pairs):
    return [x[0] for x in pairs], [x[1] for x in pairs]


def gn_deviceevent(devicepath):
    from ev3local.edutil import InputDevice
    device = InputDevice(devicepath)
    events = gen_events(devicepath, (0, 1, 5))
    return device, events


def cr_dutycycle(port):
    from ev3local.pyev3 import DutyCycle
    dutycycle = DutyCycle(port)
    return dutycycle.setdutycyclesp()


def bounds(device, code):
    import ev3local.edutil
    absinfo = ev3local.edutil.absinfo(device, code)
    return (absinfo.min, absinfo.max)


def cr_scale(device, eventcode, outbounds):
    from ev3local.generator import scale
    return scale(bounds(device, eventcode), outbounds)


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