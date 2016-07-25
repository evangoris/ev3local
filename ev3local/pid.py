from ev3local.iattribute import  AttributeIteratorMixin

class PController(AttributeIteratorMixin):
    """Proportional controller

    Object that implements a proportional controller and
    a feedback loop.

    Args:
        kp (float): Proportional gain
        max (float): Maximum on output
        min (float): Minimum on output
    """
    def __init__(self, kp, kd, max=None, min=None):
        self.KP = kp
        self.KD = kd
        self.SetPoint = 0.0
        self.ProcesVariable  = 0.0
        self.ControlVariable = 0.0
        self._maxcontrol = max
        self._mincontrol = min

        self._perror = 0.0
        self._ptime = 0.0

    def iprocess(self, isetpoint, iprocessvariable):
        import itertools
        for setpoint, processvariable in itertools.izip(isetpoint, iprocessvariable):
            self.ProcesVariable = processvariable
            self.SetPoint = setpoint
            self.step()
            yield self.ControlVariable

    def step(self):

        # Compute unbounded control variable
        #
        import time
        now = time.time()
        error  = self.SetPoint - self.ProcesVariable
        derror = error - self._perror
        dtime  = now - self._ptime

        controlv = self.KP*error + self.KD*derror / dtime

        # Claimp within (mincontrol, maxcontrol)
        #
        if self._maxcontrol and controlv>self._maxcontrol:
            controlv = self._maxcontrol
        elif self._mincontrol and controlv<self._mincontrol:
            controlv = self._mincontrol

        # Set the control variable
        #
        self.ControlVariable = controlv

        # Save state for next step
        #
        self._ptime = now
        self._perror = error
