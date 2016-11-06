#!/usr/bin/python
import sys
sys.path.append('/home/robot/src/ev3local')

import threading
class ControlLoop(threading.Thread):

    def __init__(self, freq):
        super(ControlLoop, self).__init__(target=self._loop)
        self._delay = 1.0 / float(freq)
        self._continue = True

    def __del__(self):
        self.stop()

    def _loopbody(self, *args):
        raise NotImplementedError

    def _loop(self, *args):
        import time
        while self._continue:
            self._loopbody(*args)
            time.sleep(self._delay)

    def stop(self):
        self._continue = False

class DriveControlLoop(ControlLoop):

    def __init__(self, freq, port):
        super(DriveControlLoop, self).__init__(freq)
        self._duty_cycle_sp = 0
        self._port = port

    def _loop(self):
        import ev3local.ev3
        with ev3local.ev3.TachoMotor(self._port) as motor:
            motor.run_direct()
            super(DriveControlLoop, self)._loop(motor)

    def set_duty_cycle_sp(self, sp):
        self._duty_cycle_sp = sp

    def get_duty_cycle_sp(self):
        return self._duty_cycle_sp

    Duty_Cycle_SP = property(get_duty_cycle_sp, set_duty_cycle_sp)

    def _loopbody(self, motor):
        value = int(self.Duty_Cycle_SP)
        motor.Duty_Cycle_SP = value

class SteerControlLoop(ControlLoop):

    def __init__(self, freq, port, maxcontrol=100.0, fadezone=60.0):
        super(SteerControlLoop, self).__init__(freq)

        import ev3local.pid
        kp = maxcontrol / fadezone
        kd = 0.05
        self._pid = ev3local.pid.PController(kp, kd, maxcontrol, -maxcontrol)
        self._port = port

    def set_setpoint(self, value):
        self._pid.SetPoint = value

    def get_setpoint(self):
        return self._pid.SetPoint

    SetPoint = property(get_setpoint, set_setpoint)

    def _loop(self):
        import ev3local.ev3
        with ev3local.ev3.TachoMotor(self._port) as motor:
            motor.run_direct()
            super(SteerControlLoop, self)._loop(motor)

    def _loopbody(self, motor):
        self._pid.ProcesVariable = motor.Position
        self._pid.step()
        value = int(self._pid.ControlVariable)
        motor.Duty_Cycle_SP = value

def drivecontrolcallback(drivecontrolloop):
    def f(value):
        drivecontrolloop.Duty_Cycle_SP = value
    return f

def steercontrolcallback(steercontrolloop):
    def f(value):
        steercontrolloop.SetPoint = 720*value
    return f

def main():
    import ev3local.xbox as xbox
    import ev3local.pid

    inputeventloop = xbox.XCEvents()

    steercontrolloop = SteerControlLoop(30, 'outB')
    drivecontrolloop = DriveControlLoop(30, 'outA')

    inputeventloop.connectaxes(drivecontrolcallback(drivecontrolloop), 49, 100, 0)
    inputeventloop.connectaxes(steercontrolcallback(steercontrolloop), 2, -1.0, 1.0)

    try:
        inputeventloop.start()
        steercontrolloop.start()
        drivecontrolloop.start()
        print "Controlloops started"
        while True:
            import time
            time.sleep(0.5)
    finally:
        inputeventloop.stop()
        steercontrolloop.stop()
        drivecontrolloop.stop()

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
