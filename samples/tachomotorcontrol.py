#!/usr/bin/python
import sys
sys.path.append('/home/robot/src/ev3local')

from ev3local.ev3 import TachoMotor
#from ev3local.xbox import XCEvents


def main():
    tachomotorA = TachoMotor('outA')
    tachomotorB = TachoMotor('outB')
    tachomotorA.run_direct()
    tachomotorB.run_direct()

    try:
        devicepath = pscontroller()
        print "Controller found. Input loop started."

        events1 = gen_events(devicepath, 1)
        values1 = gen_scaledvalue(events1, -50, 50)

        events2 = gen_events(devicepath, 5)
        values2 = gen_scaledvalue(events2, -50, 50)
        values2 = (-1*v if v else None for v in values2)

        import itertools
        for value1, value2 in itertools.izip(values1, values2):
            if value1:
                tachomotorA.Duty_Cycle_SP = int(value1)
            if value2:
                tachomotorB.Duty_Cycle_SP = int(value2)
            import time
            time.sleep(1.0/60.0)

    finally:
        tachomotorA.reset()
        tachomotorB.reset()

    """
    inputeventloop = XCEvents()

    def cbA(value):
        tachomotorA.Duty_Cycle_SP = int(value)

    def cbB(value):
        tachomotorB.Duty_Cycle_SP = int(value)

    inputeventloop.connectaxes(callback=cbA, axes=1, min=-50, max=50)
    inputeventloop.connectaxes(callback=cbB, axes=5, min=-50, max=50)


    try:
        inputeventloop.start()
        print "Input event loop started"
        import time
        while True:
            time.sleep(0.5)
    finally:
        inputeventloop.stop()
        tachomotorA.reset()
        tachomotorB.reset()
    """

def gen_scaledvalue(events, min, max):
    """Generate scaled values from a sequence of events

    Arguments:
        events (iter): Sequence of events
        min (float or int): Minimum of generated values
        max (float or int): Maximum of generated values

    Yields:
        float: Values in [`min`, `max`]
    """
    a = (max - min) / 256.0
    b = max - a * 255 # max = a * 255 + b

    def scale(value):
        return a * value + b

    for event in events:
        if event:
            yield scale(event.value)
        else:
            yield None

def gen_events(devicepath, code):
    """Generate EVT_ABS events from a device

    The next() method of the generator returned will return the most
    recent event since the last call to next().

    Args:
        devicepath (str): Path to device
        code (int): Code of events to generate

    Yields:
        evdev.InputEvent: Most recent event with code `code`
    """
    from evdev import InputDevice
    device = InputDevice(devicepath)

    import select
    pollobject = select.poll()
    pollobject.register(device.fd, select.POLLIN | select.POLLPRI)
    try:
        while True:
            events = pollobject.poll(0)
            if not events:
                yield None
            else:
                relevantevent = None
                for event in device.read():
                    import evdev.ecodes
                    if event.type==evdev.ecodes.ecodes['EV_ABS'] and event.code==code:
                        relevantevent = event
                yield relevantevent
    finally:
        pollobject.unregister(device.fd)

def pscontroller():
    """Find path to uinput device corresponding to a playstation controller

    Returns:
        str: Path to device

    Raises:
        RuntimeError: When no playstation controller can be found
    """
    from evdev import InputDevice, list_devices
    devices = [ (d, InputDevice(d)) for d in list_devices()]
    for path, device in devices:
        if 'PLAYSTATION' in device.name:
            return path
    raise RuntimeError("No playstation controller found")



if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
