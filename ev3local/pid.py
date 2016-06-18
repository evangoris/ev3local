from ev3local.xbox import XBoxStateController


class PController(object):
    """Proportional controller

    Object that implements a proportional controller and
    a feedback loop.

    Args:
        kp (float): Proportional gain
        setpoint (callable): Called to get the current setpoint
        pv (callable): Called to get the current value of the process variable
        out (callable): Called with the current control value
    """
    def __init__(self, kp, setpoint, pv, out):
        self._kp       = kp
        self._out      = out
        self._setpoint = setpoint
        self._pv       = pv

        # Frequency of the control loop
        #
        self._freq = 60.0

        # Thread on which the control loop is executed
        #
        self._thread = None

        # Flag to terminate the control loop
        #
        self._continue = None

    def _controlloop(self):
        """The control loop
        """
        import time

        while self._continue:

            # Get input
            #
            pv = self._pv()
            sp = self._setpoint()

            # Output control value
            #
            self._out(self._kp*(sp - pv))

            time.sleep(1.0/self._freq)

    def __enter__(self):
        """Start a thread and start the control loop on it

        Raises:
            RuntimeError: When the control loop is already running
        """

        if self._thread:
            raise RuntimeError("Controller already running")

        import threading
        self._thread = threading.Thread(target=self._controlloop)
        self._thread.deamon = True
        self._continue = True
        self._thread.start()

        return self

    def __exit__(self, type_, value, traceback):
        """Stop the control loop
        """
        self._continue = False
        self._thread.join()
        self._thread = None


def clampedcontrol(motor, maxcontrol):
    """Create a function that clamps an input signal before
    its forwarded to a motor
    """
    def out(control):
        if control>maxcontrol:
            motor.Duty_Cycle_SP = int(maxcontrol)
        elif control<-maxcontrol:
            motor.Duty_Cycle_SP = int(-maxcontrol)
        else:
            motor.Duty_Cycle_SP = int(control)

    return out


def axissetpoint(xcevents):
    """Create a function that returns the current state of an
    absolute axis of the XBox controller
    """
    state = XBoxStateController(xcevents)
    scale = 360.0

    def setpoint():
        return float(state.pvalue * scale)

    return setpoint


def processvariable(motor):
    """Create a function that returns the current position of a motor
    """
    def pv():
        return float(motor.Position)

    return pv