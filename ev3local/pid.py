class PController(object):
    """Proportional controller

    Object that implements a proportional controller and
    a feedback loop.

    Args:
        kp (float): Proportional gain
        max (float): Maximum on output
        min (float): Minimum on output
    """
    def __init__(self, kp, max=None, min=None):
        self.KP = kp
        self.SetPoint = 0.0
        self.ProcesVariable = 0.0
        self.ControlVariable = 0.0
        self._maxcontrol = max
        self._mincontrol = min


    def step(self):

        # Compute unbounded control variable
        #
        controlv = self.KP*(self.SetPoint - self.ProcesVariable)

        # Claimp within (mincontrol, maxcontrol)
        #
        if self._maxcontrol and controlv>self._maxcontrol:
            controlv = self._maxcontrol
        elif self._mincontrol and controlv<self._mincontrol:
            controlv = self._mincontrol

        # Set the control variable
        #
        self.ControlVariable = controlv
