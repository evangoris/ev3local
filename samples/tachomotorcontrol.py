#!/usr/bin/python

import sys
sys.path.append('/home/robot/src/ev3local')

from ev3local.xbox import gen_events, gen_scaledvalue


from ev3local.ev3 import TachoMotor


def main():
    tachomotorA = TachoMotor('outA')
    tachomotorB = TachoMotor('outB')
    tachomotorA.run_direct()
    tachomotorB.run_direct()

    from ev3local.generator import generator
    tmA_gendutycyclesp = generator(tachomotorA.dutycyclegenerator())

    try:
        devicepath = pscontroller()
        print "Controller found. Input loop started."

        import ev3local.xbox as xbox
        from evdev import InputDevice
        device = InputDevice(devicepath)

        absinfo1 = xbox.absinfo(device, 1)
        events1 = gen_events(devicepath, 1)
        values1 = gen_scaledvalue(events1, absinfo1.min, absinfo1.max, -50, 50)

        absinfo2 = xbox.absinfo(device, 5)
        events2 = gen_events(devicepath, 5)
        values2 = gen_scaledvalue(events2, absinfo2.min, absinfo2.max, -50, 50)
        values2 = (-1*v if v else None for v in values2)

        import itertools
        for value1, value2 in itertools.izip(values1, values2):
            if value1:
                tmA_gendutycyclesp.send(int(value1))
            if value2:
                tachomotorB.Duty_Cycle_SP = int(value2)
            import time
            time.sleep(1.0/60.0)

    finally:
        tmA_gendutycyclesp.close()
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


# TODO: Factor out pattern to search for and also return the device object
#
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
